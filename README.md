# major-flashcards

A flashcard app for memorizing the [Major System](https://en.wikipedia.org/wiki/Mnemonic_major_system) — a mnemonic technique that encodes numbers 00–99 as words using consonant sounds.

## Features

- **Three modes**: In Order, Random, Most Wrong (sorted by error rate)
- **Inverse mode**: Show the word, recall the number
- **Statistics**: Bar chart of wrong % per card
- **Session log**: History of completed runs with score and time
- **Image support**: Shows `.webp` images alongside words

## Requirements

- Python 3.10+
- PySide6

```
pip install PySide6
```

## Usage

```
python flashcards.py
```

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| Space | Flip card |
| Enter | Mark correct |
| Delete / Backspace | Mark wrong |
| ← / → | Navigate cards |

## Word List (00–99)

| # | Word | # | Word | # | Word | # | Word | # | Word |
|---|------|---|------|---|------|---|------|---|------|
| 00 | seesaw | 01 | Sid | 02 | sun | 03 | Sam | 04 | Sarah |
| 05 | soil | 06 | sash | 07 | sock | 08 | safe | 09 | sap |
| 10 | dice | 11 | dodo | 12 | Donna | 13 | Dom | 14 | door |
| 15 | doll | 16 | Deji | 17 | duck | 18 | Doof | 19 | dip |
| 20 | nose | 21 | net | 22 | Nunu | 23 | Nemo | 24 | nori |
| 25 | nail | 26 | Notch | 27 | nuke | 28 | knife | 29 | Nepo |
| 30 | moose | 31 | mud | 32 | moon | 33 | mummy | 34 | Mario |
| 35 | mole | 36 | Mochi | 37 | Mike | 38 | muff | 39 | mop |
| 40 | rose | 41 | rod | 42 | Ron | 43 | Remy | 44 | Rory |
| 45 | Rell | 46 | Raj | 47 | rake | 48 | Rafa | 49 | rope |
| 50 | Lisa | 51 | lid | 52 | lion | 53 | lime | 54 | Larry |
| 55 | Lulu | 56 | leech | 57 | Luke | 58 | leaf | 59 | Lip |
| 60 | Jessie | 61 | jet | 62 | Jennie | 63 | gem | 64 | jar |
| 65 | jello | 66 | JJ | 67 | Jackie | 68 | Jeff | 69 | Jeep |
| 70 | case | 71 | cod | 72 | Ken | 73 | Kim | 74 | choir |
| 75 | kale | 76 | cage | 77 | Keke | 78 | coffee | 79 | cab |
| 80 | fez | 81 | foot | 82 | fan | 83 | foam | 84 | fire |
| 85 | file | 86 | fudge | 87 | fake | 88 | fufu | 89 | fob |
| 90 | bus | 91 | bat | 92 | bun | 93 | bam | 94 | bear |
| 95 | ball | 96 | bush | 97 | bike | 98 | beef | 99 | baby |
