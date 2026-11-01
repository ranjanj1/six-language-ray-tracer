# Comparison and timing tool

`compare.py` checks a picture (`out.ppm`, ASCII P3) against `../reference.ppm`: every red, green and blue value of every pixel is compared, and a picture is accepted
if no value differs by more than 1. `run.py` builds each program with the commands below, runs it five times in fresh processes (alternating the order across
languages), refuses to record a time if a picture does not match, and writes `../results/<language>.json`.

| Language | Source | Build | Run |
|---|---|---|---|
| python | main.py | none | python3 main.py |
| javascript | main.js | none | node main.js |
| go | main.go | go build -o program main.go | ./program |
| java | Main.java | javac -d . Main.java | java -cp . Main |
| cpp | main.cpp | c++ -std=c++17 -O3 -ffp-contract=off main.cpp -o program | ./program |
| rust | main.rs | rustc -O -C codegen-units=1 main.rs -o program | ./program |

Wall time covers starting the process, rendering, writing the picture and exiting; compiling and the picture check are not timed.
`versions.sh` prints the toolchain versions.
