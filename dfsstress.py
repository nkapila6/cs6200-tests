#!/usr/bin/python3

""" Distributed File System Stress Test """

from typing import List, Tuple
import sys
import zlib
import os
import time

def stress(num_client_files: int, server_dir: str, client_dirs: List[str]) -> None:
    """ Run the stress tests. """

    run_id = int(time.time() * 1e6)

    # Create the files for creation
    client_filenames, client_file_crcs = create_files(client_dirs, run_id, 'create', num_client_files)

    create_start_time = time.time()
    verify_files(server_dir, client_dirs, client_filenames, client_file_crcs, num_client_files)
    create_elapsed_time = time.time() - create_start_time
    print(f'Time to create {num_client_files} files: {create_elapsed_time}')

    # Create the files for modify and sync
    client_filenames, client_file_crcs = create_files(client_dirs, run_id, 'sync', num_client_files)

    modify_start_time = time.time()
    verify_files(server_dir, client_dirs, client_filenames, client_file_crcs, num_client_files)
    modify_elapsed_time = time.time() - modify_start_time
    print(f'Time to modify {num_client_files} files: {modify_elapsed_time}')

    # Create the files, but no change, should be faster?
    client_filenames, client_file_crcs = create_files(client_dirs, run_id, 'sync', num_client_files)

    nochange_start_time = time.time()
    verify_files(server_dir, client_dirs, client_filenames, client_file_crcs, num_client_files)
    nochange_elapsed_time = time.time() - nochange_start_time
    print(f'Time to recreate but not change {num_client_files} files: {nochange_elapsed_time}')

    # Delete the files from the directory they were originally created.
    for client_dir in client_dirs:
        for client_filename in client_filenames[client_dir]:
            filename = os.path.join(client_dir, client_filename)
            while not os.path.exists(filename):
                time.sleep(1)
            os.remove(filename)

    delete_start_time = time.time()
    verify_files(server_dir, client_dirs, client_filenames, client_file_crcs, num_client_files, check_absence=True)
    delete_elapsed_time = time.time() - delete_start_time
    print(f'Time to delete {num_client_files} files: {delete_elapsed_time}')


def create_files(client_dirs: str, run_id, tag: str, num_client_files: int) -> Tuple[dict, dict]:
    """ Create files. """
    # Dicts of list, key is the directory name.
    client_file_crcs = {}
    client_filenames = {}

    for client_dir in client_dirs:
        client_dir_crc = zlib.crc32(bytes(client_dir, 'UTF-8'))

        client_filenames[client_dir] = []
        client_file_crcs[client_dir] = []
        for num in range(num_client_files):
            client_filename = f'dfsstress-{run_id}-{client_dir_crc}-{num}.txt'
            client_filenames[client_dir].append(client_filename)

            client_content = bytes(f'originally from {client_dir}, file {num}, tag {tag}\n', 'UTF-8')
            client_file_crcs[client_dir].append(zlib.crc32(client_content))

            filename = os.path.join(client_dir, client_filename)
            with open(filename, 'wb') as file:
                file.write(client_content)

    return client_filenames, client_file_crcs

def verify_files(
        server_dir: str,
        client_dirs: str,
        client_filenames: dict,
        client_file_crcs: dict,
        num_client_files: int,
        check_absence=False
    ) -> None:
    """ Verify files. """
    # Wait for the server and all the clients to have all the files,
    # Expect (client_dirs + 1) * client_dirs * num_client_files total.
    files_count = 0
    while files_count < (len(client_dirs) + 1) * len(client_dirs) * num_client_files:
        for check_dir in [server_dir] + client_dirs:
            # Check the directory for all the files except its own
            for client_dir in client_dirs:
                if client_dir == check_dir:
                    continue

                for num in range(num_client_files):
                    client_filename = client_filenames[client_dir][num]

                    filename = os.path.join(check_dir, client_filename)
                    if not os.path.exists(filename):
                        # If we're checking for absence, this is the success case
                        if check_absence:
                            files_count += 1

                        continue

                    # It might be possible that this read is done while
                    # the client is still storing.
                    crc = 0
                    with open(filename, 'rb') as file:
                        crc = zlib.crc32(file.read())

                    expected_crc = client_file_crcs[client_dir][num]
                    if crc != expected_crc:
                        # Uncomment for debugging if it gets stuck in the loop
                        # print(f'Invalid CRC for file: {filename}, expected {expected_crc}, got {crc}')
                        pass
                    else:
                        files_count += 1


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(f'Syntax: {sys.argv[0]} number-of-files /server/mount /client1/mount [/client2/mount...]')
        sys.exit(1)

    while True:
        stress(int(sys.argv[1]), sys.argv[2], sys.argv[3:])
