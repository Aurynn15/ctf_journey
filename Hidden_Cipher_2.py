encoded = [                                         #list dari nilai-nilai yang merupakan hasil perkalian antara kode ASCII dari karakter dalam pesan tersembunyi dengan key, dimana setiap nilai dalam list encoded dapat dibagi dengan key untuk mendapatkan kode ASCII yang sebenarnya, yang kemudian dapat dikonversi menjadi karakter untuk membentuk pesan tersembunyi
    1120, 1050, 990, 1110, 670, 840, 700, 1230,
    1090, 520, 1160, 1040, 950, 980, 510, 1040,
    490, 1100, 1000, 950, 990, 490, 1120, 1040,
    510, 1140, 950, 1020, 570, 500, 1020, 560,
    480, 510, 1010, 1250
]

key = 10

flag = ""

for value in encoded:               #menggunakan loop untuk mengiterasi setiap nilai dalam list encoded, membagi nilai tersebut dengan key untuk mendapatkan kode ASCII, dan kemudian mengkonversi kode ASCII tersebut menjadi karakter menggunakan fungsi chr(), dan menambahkan karakter tersebut ke string flag untuk membentuk pesan yang tersembunyi
    ascii_code = value // key       #membagi setiap nilai dalam list encoded dengan key untuk mendapatkan kode ASCII yang sebenarnya, karena nilai dalam encoded merupakan hasil perkalian antara kode ASCII dan key
    flag += chr(ascii_code)         #mengkonversi kode ASCII yang diperoleh menjadi karakter menggunakan

print(flag)                         #mencetak string flag yang telah terbentuk setelah mengiterasi semua nilai dalam list encoded dan mengkonversinya menjadi karakter, sehingga menghasilkan pesan tersembunyi yang dapat dibaca.