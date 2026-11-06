# Tutorial: build IPA dari NSP di Windows

Panduan ini membawamu dari PC Windows biasa sampai ke IPA yang siap disideload ke iPhone atau iPad.

## 0. Syarat perangkat

- **PC:** Windows 10/11 64-bit, disk kosong sekitar 2× ukuran NSP + 10 GB.
- **iPhone/iPad:** iOS / iPadOS 26 atau lebih baru, dengan chip **A17 Pro atau lebih baru** (iPhone 15 Pro ke atas) atau iPad **M1 ke atas**.
- **Milikmu sendiri:** dump game (NSP/XCI, plus update dan DLC kalau ada) dan `prod.keys`.

## 1. Pasang alat (sekali saja)

Buka **PowerShell** (tombol Start, ketik `PowerShell`, Enter), lalu jalankan:

```
winget install --id LLVM.LLVM -e
winget install --id Microsoft.DotNet.SDK.10 -e
winget install --id KhronosGroup.VulkanSDK -e
winget install --id Meta.Zstandard -e
python -m pip install lz4 capstone fonttools pillow
```

Python harus sudah terpasang (python.org, versi 3.10 atau lebih baru). Dua alat dari Apple perlu login Apple ID gratis di developer.apple.com/download:

1. **Metal Developer Tools for Windows.** Install, lalu catat foldernya (misalnya `E:\ProjectIOS\Metal Developer Tools`).
2. **Xcode 26 atau 27** (file `.xip`). Ekstrak SDK iPhone darinya, cukup sekali (sekitar 1–2 menit):
   ```
   cd E:\ProjectIOS\nxnative-win
   python win\sdk\extract_xip.py E:\ProjectIOS\Xcode_27.1.xip
   ```

Setelah itu salin `win\toolchain.example.json` menjadi `win\toolchain.json`, lalu sesuaikan path-nya. Di PC ini file tersebut sudah terisi.

## 2. Cek semua alat

Selalu jalankan dari folder repo:

```
cd E:\ProjectIOS\nxnative-win
python win\doctor.py
```

Semua baris harus `[ok ]`, dan di akhir harus muncul `everything a build needs is there`. Kalau ada yang `MISSING`, baris `get it:` di bawahnya menjelaskan cara memasangnya.

## 3. Siapkan folder game

Pakai **satu folder untuk satu game**. Isinya:

- NSP base game (wajib)
- NSP update dan DLC (opsional; yang dipakai adalah versi terbaru di folder itu)
- `prod.keys` (boleh juga di folder lain)

Contoh:

```
E:\ProjectIOS\Games\
  Balatro [0100CD801CE5E000][v0].nsp
  Balatro [0100CD801CE5E800][v851968].nsp     ← update 1.1.3, versi yang diuji upstream (disarankan)
  prod.keys
```

## 4. Build IPA

### Cara mudah: GUI

Klik dua kali **`Build-IPA-GUI.bat`** di folder `E:\ProjectIOS\nxnative-win`. Jendelanya berbahasa Inggris dengan tema hitam-pink. Lalu:

1. **Game files**: klik kotak bergaris untuk memilih NSP/XCI (base, update, DLC dari satu game), atau pakai *Choose folder*.
2. **prod.keys**: klik *Browse*.
3. Klik **Build IPA**. Tombolnya berubah jadi progress bar. Setelah selesai, kartu hijau menampilkan lokasi IPA dan tombol *Show in folder*.

GUI selalu memakai nilai default:

- nama app = nama game
- bundle ID = `org.nxnativewindows.<title ID>`
- bahasa = bawaan game
- IPA disimpan di samping file game (bisa diganti lewat *Change*)

Log tampil di bagian *Details*.

Kalau satu folder berisi beberapa game, GUI memisahkan file yang dipilih ke folder `<TitleID>_nxw` lewat hard link. Cara ini tidak memakan ruang disk tambahan.

### Lewat terminal

```
cd E:\ProjectIOS\nxnative-win
python win\build_ipa_windows.py "E:\ProjectIOS\Games" -k "E:\ProjectIOS\Games\prod.keys"
```

Tahap-tahapnya:

1. build `nx_extract`
2. ekstrak NSP
3. rewrite modul game
4. shader
5. build app (clang + ld64.lld)
6. pack IPA

Hasilnya ada di folder game, misalnya `E:\ProjectIOS\Games\Balatro.ipa`. Folder kerja `<TitleID>_build\` disimpan supaya build berikutnya lebih cepat. Log tiap tahap ada di `<TitleID>_build\logs\`.

Opsi yang berguna (`-h` menampilkan semuanya):

| Opsi | Fungsi |
|---|---|
| `-o D:\out\Game.ipa` | Lokasi file IPA hasil build |
| `--app-name "Nama"` | Nama app di home screen |
| `-l ja` | Bahasa game |
| `--no-show-fps` | Mematikan penghitung FPS |

## 4b. Mode split: IPA kecil + folder data

Pilih **03 Package → App + data folder** di GUI, atau tambahkan `--split-data` di terminal. Di kartu yang sama ada **Increased Memory Limit On / Off** (default On; di terminal `--no-entitlements` untuk Off). Hasilnya ada dua:

- `<NamaGame>.ipa`: berisi app saja (puluhan MB), sehingga install di LiveContainer hanya beberapa detik.
- `<NamaGame>-data\`: berisi `romfs`, `msl` (shader), dan `aoc` (DLC). Folder ini dibuat lewat hard link, jadi tidak memakan ruang disk tambahan di PC.

Cara memasangnya di iPhone/iPad:

1. Install `<NamaGame>.ipa` di LiveContainer seperti biasa (langkah 5).
2. Buka app-nya sekali. Akan muncul layar **Game data needed** yang menunjukkan nama folder, ukurannya, dan langkah-langkahnya.
3. Salin seluruh folder `<NamaGame>-data` ke Documents app itu:
   - **Dari Windows:** buka app **Apple Devices** (atau iTunes), pilih iPad → **Files** → nama app → seret folder `<NamaGame>-data` ke situ.
   - **Dari iPad:** buka app **Files** → *On My iPad* → nama app, lalu tempel folder dari flashdisk, network share, atau iCloud Drive.
4. Tunggu sampai penyalinan selesai (folder besar seperti TotK bisa makan 10–30 menit), lalu tekan **Check again**. Kalau muncul "Found", tutup app sepenuhnya (geser dari app switcher) dan buka lagi.
5. Launcher muncul. Tekan **Play**.

**Cara paling mudah: Import ZIP.** Di PC, buat ZIP dari folder data. Pakai 7-Zip dengan format *zip* dan level *Store* supaya cepat: `7z a -tzip -mx=0 <NamaGame>-data.zip <NamaGame>-data`. Pindahkan ZIP itu ke iPad (Files, flashdisk, atau cloud). Di layar **Game data needed**, tekan **Import ZIP…** lalu pilih ZIP-nya. App mengekstrak sendiri ke Documents-nya:

- Bar progres menampilkan GB, jumlah file, dan sisa waktu; ada tombol **Cancel**.
- Di iOS/iPadOS 26 ke atas, ekstrak tetap jalan saat app ditinggal, dengan progres di Live Activity (layar kunci dan notifikasi), lalu muncul notifikasi "Game data imported" setelah selesai. Izinkan notifikasi saat diminta.
- ZIP dibaca langsung dari tempatnya, jadi cukup ruang untuk hasil ekstrak, ditambah ZIP itu sendiri. ZIP boleh dihapus setelah selesai.
- Setelah selesai, tekan **Close the app** lalu buka lagi.

Nama folder tidak perlu diubah, karena app mencari `romfs` di Documents dan di setiap folder tepat di dalamnya. Sign ulang tiap 7 hari hanya perlu memasang IPA kecilnya; folder data di Documents tidak hilang. Salin ulang folder data hanya setelah build baru dari game yang sama.

## 4c. The Legend of Zelda: Tears of the Kingdom

- **Versi:** pakai **1.4.3** (update `v720896`). Taruh XCI/NSP base dan NSP update 1.4.3 di satu folder. Profil resmi dibuat untuk 1.4.3; versi lain tidak mendapat patch 60 fps dan render scale.
- **Mode split sangat disarankan.** Datanya sekitar 17 GB, jadi IPA tunggal butuh waktu sangat lama untuk sign dan install.
- **Ruang kosong di iPad:** minimal sekitar 25 GB (data, ditambah cache shader dan save).
- **Memori:** TotK memakai sampai 5 GB memori game. Aktifkan **Increased Memory Limit** saat menandatangani LiveContainer. Upstream baru menguji TotK di iPhone 17 Pro Max dan iPad Pro M2. Perangkat dengan RAM 6 GB atau chip tanpa BC texture (A16 ke bawah) berisiko ditutup iOS karena kehabisan memori.
- **Start pertama lama:** layar "Preparing shaders" memang muncul di start pertama. Tunggu sampai selesai dan jangan tutup app.
- **Hemat memori (otomatis):** di A16 ke bawah, tekstur BC diubah ke ASTC 4x4 (¼ memori RGBA8). Pengaman memori menurunkan fps ke 30 kalau sisa memori < 600 MB, dan membersihkan cache kalau < 300 MB (HUD menampilkan `GUARD`). Di perangkat 6 GB, *Metal 4 pipelines* dan *Pipeline prebuild* mati secara default, jadi tidak ada layar "Preparing pipelines" yang lama. Layar "Preparing shaders" berasal dari NXNative asli (upstream). Itu kompilasi shader Metal sekali, bukan emulator, dan di perangkat 6 GB sekarang jalan di latar belakang.
- **Kalau keluar sendiri:** ambil `log.txt` dan `log.prev.txt` dari Files → *On My iPad* → app TotK.

## 4d. Mod (patch performa, tekstur, dan lainnya)

Build Windows bisa memasang mod dengan format yang sama seperti emulator (Yuzu/Ryujinx/Eden) atau Atmosphere. Buat folder `mods` di samping file game, lalu satu folder per mod:

```
E:\ProjectIOS\Games\0100F2C0115B6000_nxw\
  mods\
    NamaMod\
      exefs\<build ID>.ips   atau   exefs\nama.pchtxt     ← patch kode
      romfs\...                                           ← file pengganti
```

- **Patch kode (`.ips`, `.pchtxt`)** dipasang lewat rewriter NXNative, sama seperti patch 60 fps resmi. Hanya patch yang build ID-nya cocok dengan versi game-mu yang dipakai; yang lain dilewati dengan pesan di log. Untuk TotK 1.4.3, build ID `main`-nya `277178b7dba1b6d4…`. Patch yang menimpa fix resmi profil juga dilewati.
- **File `romfs`** menimpa file asli game di folder data (lewat hard link, tidak memakan ruang).
- Pakai mod untuk **versi game yang sama**. Mod untuk 1.4.2 tidak cocok dengan 1.4.3.
- Setelah menambah atau menghapus mod, build ulang dan pasang IPA baru. Kalau mod-nya punya `romfs`, salin ulang juga folder data atau ZIP-nya.

## 5. Pasang ke iPhone

1. Pasang **LiveContainer** ([LiveContainer/LiveContainer](https://github.com/LiveContainer/LiveContainer)) dengan firmware penanda tangan yang bisa menambahkan *Increased Memory Limit*; SideStore, AltStore dan PlumeImpactor bisa menandatanganinya. Minta izin itu untuk **LiveContainer**, bukan untuk game-nya.
2. Di iPhone, buka *Settings → Privacy & Security → Developer Mode*, nyalakan, lalu restart. Setelah itu buka *Settings → General → VPN & Device Management* dan percayai sertifikat penandatangannya.
3. Pindahkan file `.ipa` ke iPhone (app **Files**, iCloud Drive, atau AirDrop).
4. Buka **LiveContainer**, tekan tombol install (**+**), lalu pilih `.ipa` itu. Game muncul sebagai app di dalam LiveContainer.
5. Buka game dari LiveContainer. Layar pengaturan (launcher) muncul. Tekan **Play**.

Dengan Apple ID gratis, LiveContainer harus di-sign ulang setiap 7 hari. Folder data dan save di Documents tidak hilang.

## 6. Kalau ada masalah

- **Build gagal:** pesan `[RED] ...` dan 40 baris terakhir log ditampilkan. Log lengkap ada di `<TitleID>_build\logs\`.
- **App menutup sendiri di iPhone:** buka app *Files*, masuk ke *On My iPhone → Balatro*, lalu ambil `log.txt`.
- **"this IPA uses vX, which game profile ... was not brought up on":** versi game itu belum diuji upstream. Pakai update yang tercantum di README upstream (untuk Balatro: 1.1.3).
- **Game yang butuh Mac:** build berhenti dengan pesan yang menyebut Mac host. Ini terjadi pada game yang shader-nya dibuat saat runtime lewat GLSLC, Vulkan, atau Unreal/Oodle. Game LÖVE seperti Balatro *tidak* termasuk: shader-nya dirakit ulang di Windows oleh `win\love_shaders.py`.

## 6b. Game yang shader-nya dibuat saat runtime (Portal, Fire Emblem: Three Houses, Super Mario Galaxy)

Game seperti ini mengompilasi sebagian shader saat dimainkan. Upstream menangkapnya di Mac; di sini penangkapan dilakukan di perangkatmu:

1. Build pertama berhenti dengan pesan dan membuat file `<NamaGame>-capture.ipa` di folder game.
2. Pasang IPA itu, mainkan sampai layar judul, lalu tunggu sekitar satu menit. Layar boleh hitam atau kosong, karena shader-nya memang belum ada.
3. Buka app **Files** → *On My iPhone/iPad* → `<NamaGame> (capture)`. Salin folder `glslc_capture` (atau `vk_capture`) ke folder game di PC, di samping file NSP.
4. Build lagi. Build menemukan folder itu, mencocokkannya dengan tabel profil, lalu membuat IPA yang sebenarnya.

Game Oodle/Unreal (Octopath Traveler, Bayonetta 3, Pokémon Z-A, DQ XI S, dan lainnya) tidak perlu langkah ini: decoder-nya dijalankan di emulator ARM64 di PC.

## 7. Memperbarui repo

```
cd E:\ProjectIOS\nxnative-win
git fetch upstream
git merge upstream/main
```
