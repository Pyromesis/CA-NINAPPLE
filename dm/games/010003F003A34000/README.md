# Pokémon: Let's Go, Pikachu! (`010003F003A34000`)

Update 1.0.2 (v131072) over the base game, SDK 5.4.151, Nintendo's own engine on NVN. The build uses `--romfs separate`: the 4.4 GB RomFS image is copied to the app's `Documents/romfs.img` once, and the IPA carries the translated shaders.

The profile in use is the NSP script's provisional guess (`<NSP folder>/010003F003A34000_build/profile`), not registered in this repository. On an iPhone 17 Pro Max (iOS 27.2, Increased Memory Limit) it boots to the app's launcher with its settings, and *Play* enters the game; the shader tables, saves and gameplay past the opening are still open.

## What it needs

- Nothing of its own so far beyond the Bluetooth cut below. The `--provisional` warning stays: the profile was guessed from the survey and has not been brought up on a Mac.

## Found on this game

- **Resolved: the app closed on *Play* until the Bluetooth API was cut.** The game's Bluetooth manager calls `nn::bluetooth::InitializeBle` at boot (`main+0x1139d4`) and then acquires the five BLE events for the Poké Ball Plus. `InitializeBle` starts the SDK's `btm` client, which connects to the `bt` service; the host does not serve it, and the SDK aborted inside the client (`[RED] sf: the game connects to service bt itself`, `Break#1`). `hle_bluetooth.c` makes the API inert: [Bluetooth LE (`bt`) for the Poké Ball Plus](../../../docs/reference/services.md#bluetooth-le-bt-for-the-poké-ball-plus).
