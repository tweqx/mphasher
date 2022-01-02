import sys
from time import sleep, time
import threading, queue
import requests
import random
import json
import shutil

if len(sys.argv) not in [2, 3]:
  print(f'Usage: python3 {sys.argv[0]} <domain_list.txt>')
  raise SystemExit

try:
  domains = open(sys.argv[1], 'r')
except IOError:
  stdout(f'Error: failed to read {sys.argv[1]}')
  raise SystemExit

domain_queue = queue.Queue(maxsize=1000*10)

# Printing to stdout
log_lock = threading.Lock()
def stdout(*args):
  with log_lock:
    print(*args)

# Progress backup
try:
  with open("./progress/progress.json", "r") as progress:
    current_progress = json.loads(progress.read())
except:
  current_progress = { "lines_done": 0 }
lines_to_skip = current_progress["lines_done"]

PROGRESS_SAVE_INTERVAL = 15*60 # 15 minutes
def save_progress():
  # Backup progress file
  try:
    shutil.copyfile("./progress/progress.json", f'./progress/progress-{time()}')
  except:
    # File doesn't exist
    pass

  # Save new progress to file
  with open("./progress/progress.json", "w") as progress:
    progress.write(json.dumps(current_progress))

  stdout("[progress] Saved progress")

  # Schedule next call
  threading.Timer(PROGRESS_SAVE_INTERVAL, save_progress).start()
save_progress()

def update_progress(lines_done):
  current_progress['lines_done'] = lines_done

# Counter
domain_counter = lines_to_skip
delta_counts = 0
counter_lock = threading.Lock()
def counter_main():
  global delta_counts

  while True:
    update_progress(domain_counter)
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
PATTERNS = [ # Pattern should be limited to ~1024 chars
  (b".jpg", ".jpg"),
  (b"FFD8FFE0", "JPG bytes"),
  (b"-----BEGIN PGP MESSAGE-----", "PGP message")
]

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
      r = requests.get(f'http://{domain}',
        headers={
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
        },
        timeout=TIMEOUT,
        stream=True # Prevents heap fragmentation
      )

      # Reading content
      buffer = b""

      for chunk in r.iter_content(chunk_size=1024):
        # Hash response
        # TODO

        # Check response for .jpg, JPG header and PGP messages
        buffer = buffer[-1024:] + chunk

        farthest_match = 0
        while farthest_match >= 0:
          farthest_match = -1

          for pattern, name in PATTERNS:
            try:
              index = buffer.index(pattern)
              farthest_match = max(farthest_match, index)

              log(f'{name} in {domain}')
            except ValueError:
              pass

          buffer = buffer[farthest_match+1:]

      # Close request
      r.close()

    except requests.TooManyRedirects:
      #log(f'Too many redirects for {domain}')
      pass
    except requests.Timeout:
      #log(f'Timeout for {domain}')
      pass
    except requests.ConnectionError as err:
      #if "Name or service not known" not in str(err):
        #log(f'Connection error for {domain}: {err}')
      pass
    except Exception as err:
      log(f'Error for {domain}: {err}')
      pass

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
