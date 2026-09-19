# TEST 2 — Process Log: NOMAD Service Pass (Sep 18 2026)

Record of the fix + cleanup process performed on the portable pendrive OS so it
can be repeated or audited.

> After this log was written, Pass 3 was completed on the same OS: it now runs
> as **Luke** (earlier "Luke Ubuntu") with an Android-style GUI — see **TEST 3.md**. The title
> above kept "NOMAD" because that was the OS name at the time the pass was done.

## 1. Context
- Host machine on which the work was done: Linux Mint 22.3 (Mint) — user `aman`.
- Target: portable Ubuntu 24.04 on SanDisk pendrive `/dev/sdb`
  (old name PORTOS, now renamed NOMAD), mounted read/write by the host at
  `/media/aman/PORTOS-ROOT` (later `/media/aman/NOMAD-ROOT`).
- All system changes were made inside the target via `chroot`.

## 2. Prerequisites / access
- Root on the host = needed for `mount`, `chroot`, `blkid`, relabeling.
  `sudo -S` was used with the host sudo password piped in each command.
- Mount the target's virtual filesystems so tools inside the chroot can work:
  ```bash
  sudo mount --bind /proc <root>/proc
  sudo mount --bind /sys  <root>/sys
  sudo mount --bind /dev  <root>/dev
  sudo mount --bind /run  <root>/run
  ```

## 3. Diagnosis (in order)
1. Disk usage: `du -h -d1 <root>`
   - Found: 7.9 GB used on the 19.5G system partition.
   - `/var/cache/apt` = 1.2 GB (largest easy win).
2. Largest packages (chroot): `dpkg-query -W --showformat='${Installed-Size}\t${Package}\n' | sort -rn`
   - linux-firmware 474M (kept — WiFi/GPU firmware), libllvm/tril 357M,
     snapd 130M, linux-headers 111M, bpftrace+clang deps, linux-tools/perf.
3. Health checks: `dpkg --audit` and `apt-get check` → clean (no broken packages).
4. fstab UUIDs cross-checked against `blkid` → matched; boot config fine.
5. Kernel was STALE: only 6.8.0-31 installed while repo offered 6.8.0-139 →
   a pending security gap (this was the main "issue").

## 4. Fixes applied
1. `apt-get update` — refreshed lists.
2. `apt-get full-upgrade -y` — installed kernel **6.8.0-139** + 131 updates,
   regenerated initramfs + GRUB (Mint dual-boot entry preserved).
3. Purged snap backend (see removal list below).
4. Pinned as MANUAL before autoremove (they were auto-flagged for removal but are
   required): `apt-mark manual apparmor grub-pc-bin openssh-client`.
5. `apt-get autoremove --purge -y` — removed dev tooling and snap leftovers.
6. Removed the old kernel completely:
   `apt-get purge linux-image-6.8.0-31-generic linux-modules-*(31) linux-headers-*(31)`.
7. `apt-get clean` — cleared the 1.2 GB package cache.
8. `journalctl --vacuum-size=15M` — trimmed logs.
9. Removed current-kernel headers (compile-only, not needed on this desktop).

## 5. What was removed
- snapd + firefox stub (`1:1snap1`, the snap-transitional deb; snap image never installed)
- linux-tools-6.8.0-31 / linux-tools-generic (perf)
- bpftrace, libclang/libllvm28 chain, libc6-dev, linux-libc-dev, manpages-dev,
  libcrypt-dev, squashfs-tools, rpcsvc-proto, old kernel headers/image/modules

## 6. Rebrand — PORTOS → NOMAD
- `/etc/hostname` → `nomad`
- `/etc/hosts` → `127.0.1.1    nomad`
- `/etc/os-release` + `/etc/lsb-release` → NAME="Nomad", VERSION="1.0 (Noble base)";
  kept `ID=ubuntu`, `UBUNTU_CODENAME=noble` so apt/PPAs keep working.
- Ran `update-grub` so the boot menu now shows **"Nomad GNU/Linux"** (base entry,
  advanced/recovery entries, then Linux Mint).
- Relabeled partitions (after unmounting binds and the drive):
  ```bash
  e2label    /dev/sdb3 NOMAD-ROOT
  fatlabel   /dev/sdb2 NOMAD-EFI
  exfatlabel /dev/sdb4 NOMAD-DATA
  ```
  UUIDs unchanged → fstab + GRUB (hd1,gpt3) unaffected.
- Remounted under new host paths `/media/aman/NOMAD-{ROOT,EFI,DATA}`.

## 7. Results
- System partition: 7.9 GB → **6.8 GB used** (~1.1–2 GB freed incl. cache),
  12 GB free (38% used) on the 19.5G partition.
- Kernel now current and secure; only one kernel installed.
- `dpkg --audit` clean, `apt-get check` clean, swapfile intact.

## 8. Result of the following pass
The Android-style GUI + rebrand to **Luke** is documented separately in
**TEST 3.md**.