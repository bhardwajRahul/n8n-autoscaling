import redis
import time
import os
import logging

# --- Logging Setup ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format='%(asctime)s - %(levelname)s - %(message)s')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
QUEUE_NAME_PREFIX = os.getenv('QUEUE_NAME_PREFIX', 'bull') # BullMQ default prefix
QUEUE_NAME = os.getenv('QUEUE_NAME', 'jobs')
POLL_INTERVAL_SECONDS = int(os.getenv('POLL_INTERVAL_SECONDS', 5))

def get_redis_connection():
    """Establishes a connection to Redis."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
        r.ping()
        logging.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        return r
    except redis.exceptions.ConnectionError as e:
        logging.error(f"Error connecting to Redis: {e}")
        return None

def get_queue_length(r_conn, queue_name_prefix, queue_name):
    """Gets the length of the specified BullMQ queue."""
    # BullMQ stores lists for different states of a queue.
    # 'wait' (or the main queue list) is usually what people mean by "queue length"
    # It's typically named "bull:<queue_name>:wait" or just "bull:<queue_name>" for older versions
    # or sometimes just <queue_name_prefix>:<queue_name>
    # We'll also check for 'active', 'delayed', 'completed', 'failed' to give a fuller picture.

    # The primary list representing pending jobs is usually <prefix>:<queue_name>:wait
    # However, LLEN on <prefix>:<queue_name> itself often gives the count of waiting jobs too.
    # Let's try the most common one for "waiting" jobs.
    # BullMQ v3+ uses <prefix>:<queue_name>:wait for waiting jobs
    # BullMQ v4+ uses <prefix>:<queue_name>:waiting for waiting jobs
    # Simpler approach: BullMQ also maintains a list named just <prefix>:<queue_name>
    # which often corresponds to the 'waiting' list or is a good proxy.
    
    # For BullMQ, the key for the list of waiting jobs is typically `<prefix>:<queue_name>:wait`
    # or for newer versions `<prefix>:<queue_name>:waiting`.
    # The command `LLEN <prefix>:<queue_name>` often gives the count of waiting jobs.
    # Let's try to get the length of the main list for the queue.
    # BullMQ queue keys are typically prefixed, e.g., "bull:myQueueName:id"
    # The actual list of waiting jobs is often "bull:myQueueName:wait" or "bull:myQueueName:waiting"
    # However, n8n might use a simpler naming. The `KEYS` command showed `bull:jobs:active` etc.
    # This implies the base queue name is `jobs` and the prefix is `bull`.
    # The list of waiting jobs is typically `bull:<queue_name>:wait`.
    
    # Based on the `KEYS "bull:*:*"` output, `bull:jobs:active` and similar keys exist.
    # The list of *waiting* jobs is what we're interested in.
    # This is typically `bull:<queue_name>:wait` or `bull:<queue_name>:waiting`.
    # Let's try `LLEN bull:jobs:wait`
    key_to_check = f"{queue_name_prefix}:{queue_name}:wait"
    try:
        length = r_conn.llen(key_to_check)
        if length is None: # If key doesn't exist, llen might return None or an error depending on client version
             # Try the older pattern if :wait doesn't exist
            key_to_check_legacy = f"{queue_name_prefix}:{queue_name}"
            length = r_conn.llen(key_to_check_legacy)
            if length is not None:
                logging.debug(f"Using legacy key pattern '{key_to_check_legacy}' for queue length.")
                key_to_check = key_to_check_legacy # update for logging
            else:
                 # If neither exists, it might be 0 or an issue.
                 # Let's also check for the key used by BullMQ v4+
                key_to_check_v4 = f"{queue_name_prefix}:{queue_name}:waiting"
                length = r_conn.llen(key_to_check_v4)
                if length is not None:
                    logging.debug(f"Using BullMQ v4+ key pattern '{key_to_check_v4}' for queue length.")
                    key_to_check = key_to_check_v4
                else:
                    logging.warning(f"Key '{key_to_check}', '{key_to_check_legacy}', or '{key_to_check_v4}' not found or not a list. Assuming length 0.")
                    return 0
        return length
    except redis.exceptions.ResponseError as e:
        # This can happen if the key exists but is not a list type
        logging.error(f"Redis error when checking length of '{key_to_check}': {e}. Assuming length 0.")
        return 0
    except Exception as e:
        logging.error(f"Unexpected error when checking length of '{key_to_check}': {e}. Assuming length 0.")
        return 0


if __name__ == "__main__":
    redis_conn = get_redis_connection()
    if redis_conn:
        logging.info(f"Monitoring Redis queue '{QUEUE_NAME_PREFIX}:{QUEUE_NAME}' every {POLL_INTERVAL_SECONDS} seconds...")
        last_known_length = None  # Track queue length changes for event-driven logging
        try:
            while True:
                length = get_queue_length(redis_conn, QUEUE_NAME_PREFIX, QUEUE_NAME)

                # Event-driven logging: only log when queue has items or length changes
                if length > 0:
                    logging.info(f"Queue '{QUEUE_NAME_PREFIX}:{QUEUE_NAME}' length: {length}")
                elif last_known_length is not None and last_known_length > 0 and length == 0:
                    # Log when queue drains to zero (transition event)
                    logging.info(f"Queue '{QUEUE_NAME_PREFIX}:{QUEUE_NAME}' drained to 0")

                last_known_length = length
                time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user.")
        finally:
            redis_conn.close()
            logging.info("Redis connection closed.")