import sys
from time import sleep
import threading, queue
import requests
import random

if len(sys.argv) not in [2, 3]:
  print(f'Usage: python3 {sys.argv[0]} <domain_list.txt> [number of lines to skip]')
  raise SystemExit

try:
  domains = open(sys.argv[1], 'r')
except IOError:
  stdout(f'Error: failed to read {sys.argv[1]}')
  raise SystemExit

lines_to_skip = 0
if len(sys.argv) == 3:
  # Skipped lines
  lines_to_skip = int(sys.argv[2])

domain_queue = queue.Queue(maxsize=1000*10)

# Printing to stdout
log_lock = threading.Lock()
def stdout(*args):
  with log_lock:
    print(*args)

# Counter
domain_counter = lines_to_skip
delta_counts = 0
counter_lock = threading.Lock()
def counter_main():
  global delta_counts

  while True:
    with counter_lock:
      stdout(f'[counter] {delta_counts} requests/sec ; {domain_counter} requests done')

    delta_counts = 0
    sleep(1)
def counter_increase():
  global domain_counter, delta_counts

  with counter_lock:
    domain_counter += 1
    delta_counts += 1

# Workers code
TIMEOUT = 10 # seconds

def worker_main(id):
  def log(msg):
    stdout(f'[{id}] {msg}')

  log("Started")

  # Randomly delay start...
  sleep(random.randint(0, 60))

  while True:
    domain = domain_queue.get()

    # Send request
    try:
      r = requests.get(f'http://{domain}', headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
      }, timeout=TIMEOUT)
    except requests.TooManyRedirects:
      #log(f'Too many redirects for {domain}')
      pass
    except requests.Timeout:
      #log(f'Timeout for {domain}')
      pass
    except requests.ConnectionError as err:
      # Only log other errors
      #if "Name or service not known" not in str(err):
        #log(f'Connection error for {domain}: {err}')
      pass
    except Exception as err:
      #log(f'Error for {domain}: {err}')
      pass

    else:
      # Hash response
      # TODO

      # Check response for .jpg, JPG header, and PGP messages
      upper_response = r.text.upper()

      if "-----BEGIN PGP MESSAGE-----" in upper_response:
        log(f'PGP in {domain}')
      if ".JPG" in upper_response:
        log(f'.jpg in {domain}')
      if "FFD8FFE0" in upper_response:
        log(f'JPG bytes in {domain}')

    counter_increase()
    domain_queue.task_done()

stdout('[main] Starting counter')
counter_thread = threading.Thread(target=counter_main, name='counter_thread')
counter_thread.daemon = True
counter_thread.start()

stdout('[main] Starting all threads')

# Thread creation
WORKERS_COUNT = 600

workers = []
for id in range(WORKERS_COUNT):
  worker_thread = threading.Thread(target=worker_main, args=(id,), name=f'worker-{id}')
  worker_thread.daemon = True
  worker_thread.start()

  workers.append(worker_thread)

stdout('[main] All threads started')

# Feeding domain names to threads...
for index, line in enumerate(domains):
  # Line skipping...
  if index < lines_to_skip:
    continue

  domain = line[:-1] # Remove newline

  domain_queue.put(domain)

stdout('[main] All domains sent to the queue')

domain_queue.join()

stdout('[main] All domains consumed, bye!')
