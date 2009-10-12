DB = commits.db

all: $(DB)

$(DB): commits.sql
	sqlite3 $@ < $<

clean:
	rm $(DB)
	find . -name '*.py[co]' -exec rm {} \;

fresh: clean all

.PHONY: all clean fresh

