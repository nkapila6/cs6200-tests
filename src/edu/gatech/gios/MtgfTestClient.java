package edu.gatech.gios;

import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.net.Socket;
import java.net.ConnectException;
import java.io.IOException;
import java.io.OutputStream;
import java.io.InputStream;

/**
 * Multi-Threaded GetFile Test Client by Miguel Paraz <mparaz@gatech.edu>
 * Command line: number-of-workers minimum-delay-in-milliseconds maximum-delay
 */
public class MtgfTestClient implements Runnable {
    private final int testOption;
    private final int workerId;
    private final int minDelay, maxDelay;

    public MtgfTestClient(int testOption, int workerId, int minDelay, int maxDelay) {
        this.testOption = testOption;
        this.workerId = workerId;
        this.minDelay = minDelay;
        this.maxDelay = maxDelay;
    }

    public static void main(String[] args) throws InterruptedException {
        final int testOption = Integer.parseInt(args[0]);
        final int workers = Integer.parseInt(args[1]);
        final int minDelay = Integer.parseInt(args[2]);
        final int maxDelay = Integer.parseInt(args[3]);

        final ExecutorService executorService = Executors.newFixedThreadPool(workers);

        for (int i = 0; i < workers; i++) {
            executorService.execute(new MtgfTestClient(testOption, i, minDelay, maxDelay));
        }

        // Just wait indefiniteiy...
        Thread.sleep(86400);
    }

    @Override
    public void run() {
        final Random random = new Random();

        // More than enough...
        final byte[] buffer = new byte[8192];

        final String header;
        
        if (testOption == 1) {
            // Just send a nonexistent path. We're not testing I/O.
            header = "GETFILE GET /worker" + workerId + "\r\n\r\n";
        } else {
            // Send a request for an existing path.
            header = "GETFILE GET /courses/ud923/filecorpus/paraglider.jpg\r\n\r\n";
        }
        
        while (true) {
            try {
                final Socket socket = new Socket("127.0.0.1", 10823);
                final OutputStream outputStream = socket.getOutputStream();
                final InputStream inputStream = socket.getInputStream();

                outputStream.write(header.getBytes());

                // Need to read the socket fully.
                // Otherwise, server will report connection reset by peer
                // (which is not being tested now)
                while (inputStream.read(buffer) > 0);

                socket.close();

                // Delay
                final int delay;
                if (minDelay == maxDelay) {
                    delay = minDelay;
                } else {
                    delay = random.nextInt(maxDelay - minDelay) + minDelay;
                }

            Thread.sleep(delay);

            } catch (ConnectException e) {
                // The server is dead, just shut down worker.
                e.printStackTrace();
                return;
            } catch (IOException e) {
                // The socket is dead, reopen.
                e.printStackTrace();
            } catch (InterruptedException e) {
                // Shut down worker.
                e.printStackTrace();
                return;
            }
        }
    }
}
