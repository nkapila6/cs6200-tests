""" Getfile Test Server for Abnormal Cases """
import socket
import time
import random
import hashlib
import sys

# Hello, OMSCS 6200 GIOS Spring 2022!
# By: Miguel Paraz <mparaz@gatech.edu>

if __name__ == "__main__":
    # Which option to test
    option = sys.argv[1] if len(sys.argv)>2 else 1

    ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ss.bind(("127.0.0.1", 10823))
    ss.listen(5)

    while True:
        s, t = ss.accept()

        # Receive and show the header, don't do anything with it
        print(s.recv(8192))

        
        if option == 1:
            # Option 1.  # Do not send anything.
            # Break this server and the client recv() may ECONNRESET if it is waiting for data.
            pass
        elif option == 2:
            # Option 2. Send the header, in two pieces. Then send 1 byte payload. Client should succeed.
            s.send(b"GETFILE OK ")
            time.sleep(1)
            s.send(b"1\r\n\r\nX")
        elif option == 3:
            # Option 3. Send the header, in pieces, with enough time to interrupt. Then send 1 byte payload.
            # Break this server to cause ECONNRESET on the client recv() in the header processing.
            s.send(b"GETFILE OK ")
            time.sleep(3600)
            s.send(b"1\r\n\r\nX")
        elif option == 4:
            # Option 4. Send rubbish payload, slowly. Break this server to cause ECONNRESET on the client recv()
            # in the payload processing.
            s.send(b"GETFILE OK 123456789\r\n\r\n")
            while True:
                s.send(b"abcd")
                time.sleep(1)
        elif option == 5:
            # Option 5. Send a non-decimal length
            s.send(b"GETFILE OK badlengthisbad\r\n\r\n")
        elif option == 1000:
            # Serve a 2 GB + 1 (exceeds int) file
            # This can be verified with: sha1sum filename.
            hash = hashlib.sha1()
            size = 2**31 + 1

            s.send(bytes(f"GETFILE OK {size}\r\n\r\n", "UTF-8"))
            while size > 0:
                buffer_size = 8192
                random_buffer = bytes([random.randint(0, 255) for _ in range(0, buffer_size)])
                hash.update(random_buffer)
                s.send(random_buffer)
                size -= buffer_size

            print(hash.hexdigest())            
        else:
            # Serve a random sized file with random-sized buffers of random bytes, and show the SHA1 hash.
            # This can be verified with: sha1sum filename.
            hash = hashlib.sha1()
            size = random.randint(10_000, 1_000_000)

            # numpy? from Vladimir.
            # random_buffer = np.random.bytes(buffer_size)


            s.send(bytes(f"GETFILE OK {size}\r\n\r\n", "UTF-8"))
            while size > 0:
                buffer_size = random.randint(min(100, size), min(1_000, size))
                random_buffer = bytes([random.randint(0, 255) for _ in range(0, buffer_size)])
                hash.update(random_buffer)
                s.send(random_buffer)
                size -= buffer_size

            print(hash.hexdigest())
            
