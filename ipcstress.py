""" IPC Stress Test """
#
# Create a workload (use shell commands)
# Start the simplecached
# Start the webproxy
# Run gfclient_download
# Verify file checksums

from typing import List

import os
import shutil
import sys
import glob
import subprocess
import time
import re

# Block size for the dd command.
DD_BLOCK_SIZE = 16

# Use some powers of two plus some multiple of the dd block size,
# to make generation reasonably fast.
WORKLOAD_SIZES = [
    1024 + 1 * DD_BLOCK_SIZE,
    4096 + 7 * DD_BLOCK_SIZE,
    65536 + 13 * DD_BLOCK_SIZE,
    262144 + 19 * DD_BLOCK_SIZE,
    1048576 + 23 * DD_BLOCK_SIZE,
    4 * 1048576 + 29 * DD_BLOCK_SIZE,
    8 * 1048576 + 31 * DD_BLOCK_SIZE,
    16 * 1048576 + 33 * DD_BLOCK_SIZE,
]

# Alternative: random sizes

# For locals.txt, for simplecached:
WORKLOAD_LOCAL_PATH = 'ipcstress_files'

# For workload.txt, for gfclient_download to store:
WORKLOAD_URL_PATH = 'ipcstress'

LOCALS_FILENAME = 'locals-ipcstress.txt'
WORKLOAD_FILENAME = 'workload-ipcstress.txt'


def run_sha1sum(filenames: List[str], output_file: str) -> None:
    """ Run sha1sum on filenames and write to an output file. """
    # Get the hashes. SHA1 is good enough for this.
    result = subprocess.run(
        ['/usr/bin/sha1sum'] + filenames,
        capture_output=True,
        check=True)

    # Store the hashes.
    with open(output_file, 'wb') as f:
        f.write(result.stdout)


def create_workload(workdir: str):
    """ Create workload. """

    # Create path or ignore if already present.
    path = f'{workdir}/{WORKLOAD_LOCAL_PATH}'
    os.makedirs(path, exist_ok=True)

    # Create the files with random content.
    filenames = []
    print('Creating workload data files:')
    for i, size in enumerate(WORKLOAD_SIZES):
        filename = f'{path}/workload{i}.bin'
        filenames.append(filename)
        nblocks = size // DD_BLOCK_SIZE

        subprocess.run([
            '/usr/bin/dd',
            'if=/dev/urandom',
            f'of={filename}',
            f'bs={DD_BLOCK_SIZE}',
            f'count={nblocks}'
        ], check=True)

    full_sha1sum_filename = f'{path}/sha1sum.txt'
    print(f'Creating SHA1 hash file: {full_sha1sum_filename}')
    run_sha1sum(filenames, full_sha1sum_filename)

    # Create the locals file.
    full_locals_filename = f'{workdir}/{LOCALS_FILENAME}'
    print(f'Creating locals file: {full_locals_filename}')
    with open(full_locals_filename, 'w') as f:
        for i, filename in enumerate(filenames):
            f.write(f'/{WORKLOAD_URL_PATH}/workload{i}.bin {filename}\n')

    # Create the workload file.
    full_workload_filename = f'{workdir}/{WORKLOAD_FILENAME}'
    print(f'Creating workload file: {full_workload_filename}')
    with open(f'{workdir}/{WORKLOAD_FILENAME}', 'w') as f:
        for i, _ in enumerate(filenames):
            f.write(f'/{WORKLOAD_URL_PATH}/workload{i}.bin\n')

    # Delete the result directory, gfclient_download will recreate it.
    shutil.rmtree(f'{workdir}/{WORKLOAD_URL_PATH}')


def run_ipcstress(
    workdir: str,
    cache_thread_count: int,
    proxy_thread_count: int,
    proxy_segment_count: int,
    proxy_segment_size: int,
    download_thread_count: int,
    request_count: int,
    port: int
) -> int:
    """ Run IPC Stress. Return 0 for normal exit. """

    popen_cache = subprocess.Popen([
        './simplecached',
        '-c',
        f'./{LOCALS_FILENAME}',
        '-t',
        str(cache_thread_count)
    ], cwd=workdir
    )
    # print(f'cache pid: {popen_cache.pid}')

    popen_proxy = subprocess.Popen([
        './webproxy',
        '-n',
        str(proxy_segment_count),
        '-p',
        str(port),
        '-t',
        str(proxy_thread_count),
        '-z',
        str(proxy_segment_size)
    ], cwd=workdir
    )
    # print(f'proxy pid: {popen_proxy.pid}')

    # Give the proxy a quarter second to start, to eliminate the client message:
    # Failed to connect.  Trying again....
    time.sleep(0.250)

    popen_download = subprocess.Popen([
        './gfclient_download',
        '-p',
        str(port),
        '-t',
        str(download_thread_count),
        '-w',
        f'./{WORKLOAD_FILENAME}',
        '-r',
        str(request_count)
    ], cwd=workdir
    )
    # print(f'download pid: {popen_download.pid}')

    while True:
        download_poll = popen_download.poll()

        # explicit "is not None" is needed because the return code may be 0
        if download_poll is not None:
            break

        if popen_cache.poll() is not None:
            print('Cache exited')
            popen_download.terminate()
            popen_proxy.terminate()
            return 1

        if popen_proxy.poll() is not None:
            print('Proxy exited')
            popen_download.terminate()
            popen_cache.terminate()
            return 2

        time.sleep(1)

    popen_cache.terminate()
    popen_proxy.terminate()

    return 0


def verify_results(workdir: str) -> str:
    """ Verify results, return True on success. """
    filenames = glob.glob(f'{workdir}/{WORKLOAD_URL_PATH}/*')
    result_filename = f'{workdir}/{WORKLOAD_URL_PATH}/sha1sum-result.txt'
    run_sha1sum(filenames, result_filename)

    # Entries in the sha1sum files are full paths.
    re_sha1sum = re.compile(r'(\w+)\s+(.*)')

    # Load the original hashes for comparison.
    workload_sha1 = {}
    with open(f'{workdir}/{WORKLOAD_LOCAL_PATH}/sha1sum.txt', 'r') as file:
        for line in file:
            match = re_sha1sum.match(line.rstrip())
            if match:
                workload_sha1[os.path.basename(match.group(2))] = match.group(1)

    # Find all the mismatching hashes.
    success = True
    with open(result_filename, 'r') as file:
        for line in file:
            match = re_sha1sum.match(line.rstrip())
            if match:
                filename = os.path.basename(match.group(2))
                workload_hash = workload_sha1.get(filename)
                if workload_hash and (workload_hash != match.group(1)):
                    print(f'Hash mismatch: {filename}')
                    success = False

    return success


def run_base_test(workdir: str):
    """ Base level of testing. """

    port = 10823
    create_workload(workdir)

    request_count = 100
    cache_thread_count = 1
    proxy_thread_count = 1
    proxy_segment_count = 1
    proxy_segment_size = 1024
    download_thread_count = 1

    print(
        f'cache_thread_count={cache_thread_count}, proxy_thread_count={proxy_thread_count}, '
        f'proxy_segment_count={proxy_segment_count}, proxy_segment_size={proxy_segment_size}, '
        f'download_thread_count={download_thread_count}, request_count={request_count}'
    )
    if run_ipcstress(
        workdir,
        cache_thread_count,
        proxy_thread_count,
        proxy_segment_count,
        proxy_segment_size,
        download_thread_count,
        request_count,
        port
    ) != 0:
        return

    if not verify_results(workdir):
        return


def run_parameter_test(workdir: str):
    """ Test through a wide range of parameters. """

    port = 10823
    create_workload(workdir)

    request_count = 10
    for cache_thread_count in range(1, 101, 10):
        for proxy_thread_count in range(cache_thread_count, 101, 10):
            for proxy_segment_count in range(1, 100):
                download_thread_count = proxy_thread_count

                proxy_segment_size = 512
                while proxy_segment_size <= 1048576:
                    print(
                        f'cache_thread_count={cache_thread_count}, proxy_thread_count={proxy_thread_count}, '
                        f'proxy_segment_count={proxy_segment_count}, proxy_segment_size={proxy_segment_size}, '
                        f'download_thread_count={download_thread_count}, request_count={request_count}'
                    )

                    if run_ipcstress(
                        workdir,
                        cache_thread_count,
                        proxy_thread_count,
                        proxy_segment_count,
                        proxy_segment_size,
                        download_thread_count,
                        request_count,
                        port
                    ) != 0:
                        return

                    if not verify_results(workdir):
                        return

                    proxy_segment_size *= 4


def run_stress_test(workdir: str):
    """ Stress test with fixed proxy segment size and number of segments. """

    port = 10823
    create_workload(workdir)

    request_count = 100
    proxy_segment_count = 50
    proxy_segment_size = 1048576

    for cache_thread_count in range(20, 101, 10):
        for proxy_thread_count in range(cache_thread_count, 101, 10):
            download_thread_count = proxy_thread_count

            print(
                f'cache_thread_count={cache_thread_count}, proxy_thread_count={proxy_thread_count}, '
                f'proxy_segment_count={proxy_segment_count}, proxy_segment_size={proxy_segment_size}, '
                f'download_thread_count={download_thread_count}, request_count={request_count}'
            )

            if run_ipcstress(
                workdir,
                cache_thread_count,
                proxy_thread_count,
                proxy_segment_count,
                proxy_segment_size,
                download_thread_count,
                request_count,
                port
            ) != 0:
                return

            if not verify_results(workdir):
                return


if __name__ == '__main__':
    workdir = sys.argv[1] if len(sys.argv) == 2 else '.'

    # Pick a test:
    run_base_test(workdir)
    # run_parameter_test(workdir)
    # run_stress_test(workdir)
