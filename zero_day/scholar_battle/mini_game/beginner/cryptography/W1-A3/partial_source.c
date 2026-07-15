// Partial decompilation -- Analis: Budi Setiawan
// Sampel: suspected_iot_config_decoder (stripped binary)
// CATATAN: nilai kunci telah diredaksi dalam versi ini

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// XOR key tersimpan di 4 byte pertama file config
uint8_t key[4] = {??};  // redacted -- lihat offset 0x00 pada config.bin

void decode_strings(const uint8_t *blob, size_t blob_len) {
    // Lewati 4 byte pertama (kunci XOR)
    const uint8_t *data = blob + 4;
    size_t remaining = blob_len - 4;

    uint8_t buf[256];
    size_t buf_idx = 0;

    for (size_t i = 0; i < remaining; i++) {
        // Terapkan XOR dengan kunci 4-byte secara siklik
        uint8_t decoded_byte = data[i] ^ key[i % 4];

        if (decoded_byte == 0x00) {
            // String selesai -- null terminator ditemukan
            buf[buf_idx] = '\0';
            printf("String: %s\n", buf);
            buf_idx = 0;
        } else {
            buf[buf_idx++] = decoded_byte;
        }
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <config.bin>\n", argv[0]);
        return 1;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("fopen"); return 1; }
    fseek(f, 0, SEEK_END); long fsize = ftell(f); rewind(f);
    uint8_t *blob = malloc(fsize);
    fread(blob, 1, fsize, f);
    fclose(f);
    memcpy(key, blob, 4);   // baca kunci dari offset 0x00
    decode_strings(blob, fsize);
    free(blob);
    return 0;
}
