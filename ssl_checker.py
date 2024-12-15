import sys
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
import ssl
import socket
import time
from datetime import datetime
import math


RUN_MULTITHREADING = True
WORKERS_COUNT = multiprocessing.cpu_count()
SOCKET_CONNECTION_TIMEOUT = 2
DAYS_THRESHOLD = 30


def get_result(result_func, log_file, host, context=False):
    # future.result() if RUN_MULTITHREADING = True
    # get_certificate_time(context, host) if RUN_MULTITHREADING = False
    try:
        result = result_func(context, host) if context else result_func()
        days_remaining, time_remaining_txt, date, ip = result.values()
        line = f"{host} {ip} {'WARN' if days_remaining < DAYS_THRESHOLD else 'OK'} {time_remaining_txt} {date}"
        print(line)
        log_file.write(f'{line}\n')
    except Exception as e:
        print(f'{host} ERROR {e}')
        log_file.write(print(f'{host} ERROR {e}\n'))

def get_certificate_time(context, host):
    h = host.split(":")[0]
    p = host.split(":")[1]
    with socket.create_connection((h, p), SOCKET_CONNECTION_TIMEOUT) as tcp_socket:
        with context.wrap_socket(tcp_socket, server_hostname=h) as ssl_session:
            ip = socket.gethostbyname(h)
            certificate_info = ssl_session.getpeercert()
            exp_date_text = certificate_info['notAfter']
            date = datetime.strptime(exp_date_text, f'%b %d %H:%M:%S %Y %Z')
            # print(certificate_info)
            # print(exp_date_text)
            # print(date)

            time_remaining = date - datetime.now()
            time_remaining_txt = format_time_remaining(time_remaining)
            days_remaining = time_remaining.days
            return {"days_remaining":days_remaining, "time_remaining_txt":time_remaining_txt, "date":date, "ip":ip}
        
def check_certificates_all(hostnames_filename):
    hostnames_file = open(hostnames_filename, "r")
    hostnames = hostnames_file.read().splitlines()
    now = datetime.now().strftime("Y-%m-%d-%H-%M-%S")
    log_file = open(f"output/log_{now}.txt", "w")
    context = ssl.create_default_context()
    endpoint_count = len(hostnames)
    print(f"[*] Checking {pluralise('endpoint', endpoint_count)}")
    log_file.write(f"[*] Checking {pluralise('endpoint', endpoint_count)}\n")

    if RUN_MULTITHREADING:
        with ThreadPoolExecutor(max_workers=WORKERS_COUNT) as executor:
            future_list = {executor.submit(get_certificate_time, context, host): host for host in hostnames}
            # print(future_list)
            for future in as_completed(future_list):
                host = future_list[future]
                try:
                    result = future.result()
                    days_remaining, time_remaining_txt, date, ip = result.values()
                    line = f"{host} {ip} {'WARN' if days_remaining < DAYS_THRESHOLD else 'OK'} {time_remaining_txt} {date}"
                    print(line)
                    log_file.write(f'{line}\n')
                except Exception as e:
                    print(f'{host} ERROR {e}')
                    log_file.write(print(f'{host} ERROR {e}\n'))
    else: 
        for host in hostnames:
            try:
                result = get_certificate_time(context, host)
                days_remaining, time_remaining_txt, date, ip = result.values()
                line = f"{host} {ip} {'WARN' if days_remaining < DAYS_THRESHOLD else 'OK'} {time_remaining_txt} {date}"
                print(line)
                log_file.write(f'{line}\n')
            except Exception as e:
                print(f'{host} ERROR {e}')
                log_file.write(print(f'{host} ERROR {e}\n'))

    #######################
    #######################
    #######################

    # if RUN_MULTITHREADING:
    #     with ThreadPoolExecutor(max_workers=WORKERS_COUNT) as executor:
    #         future_list = {executor.submit(get_certificate_time, context, host): host for host in hostnames}
    #         # print(future_list)
    #         for future in as_completed(future_list):
    #             host = future_list[future]
    #             get_result(future.result, log_file, host)
    # else: 
    #     for host in hostnames:
    #         get_result(get_certificate_time, log_file, host, context)


def pluralise(singular, count):
    return f"{count} {singular}{'' if count == 1 else 's'}"

def format_time_remaining(time_remaining):
    day_count = time_remaining.days
    seconds_per_minute = 60
    seconds_per_hour = seconds_per_minute * 60
    seconds_count = time_remaining.seconds
    hours = int(seconds_count / seconds_per_hour)
    seconds_count -= hours * seconds_per_hour
    minutes = int(seconds_count / seconds_per_minute)
    return f"{pluralise('day', day_count)} {pluralise('hour', hours)} {pluralise('min', minutes)}"

def main():
    start = time.perf_counter()
    if len(sys.argv) == 2:
        hostnames_filename = sys.argv[1]
        check_certificates_all(hostnames_filename)
    else:
        print(f'[*] Usage: {sys.argv[0]} [hostnames_filename]')
    end = time.perf_counter()
    print(f'[*] Total time: {end - start}')

if __name__ == "__main__":
    main()
