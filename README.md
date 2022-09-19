# Dockerfile Package Manager Optimizer
A tool for dockerfile package manager optimization.

## Usage
```shell
Usage: python src/main.py [OPTIONS] INPUT
If INPUT is a directory, all files (including subdirectories) in it will be optimized.

Options:
  -h            display this help message and exit
  -o OUTPUT     optimized output dockerfile path, default to INPUT + SUFFIX
                (SUFFIX is ".optimized" by default, so this will be "INPUT.optimized" by default)
                If INPUT is a directory, then OUTPUT should be a directory too
  -s SUFFIX     set the prefix of the output file, default to ".optimized"
                If INPUT and OUTPUT both are directories, then SUFFIX will be ignored 
```

### Examples:

```shell
python src/main.py -h

# File INPUT
python src/main.py Dockerfile	# Generate Dockerfile.optimized
python src/main.py -o Dockerfile1 Dockerfile	# Generate Dockerfile1
python src/main.py -s .new Dockerfile	# Generate Dockerfile.new

# Directory INPUT
python src/main.py -s .new ./dockerfiles/	# For ./dockerfiles/Dockerfile, this will generate ./dockerfiles/Dockerfile.new
python src/main.py -o ./new_dockerfiles ./dockerfiles/	# ./new_dockerfiles/ has the same structure with ./dockerfiles/
```





## Things to do next:

* Parse shell scripts
* More support for cache directory modification
* Support remove command (such as rm -r /var/lib/apt)
* Support subdirectory detection
