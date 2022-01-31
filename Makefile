all: hexdump

hexdump:hexdump.c
	$(CC) -o $@ $^
