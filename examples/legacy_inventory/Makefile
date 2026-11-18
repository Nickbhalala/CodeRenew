CXX ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Werror -O1

inventory_tests: inventory.cpp inventory_tests.cpp inventory.h
	$(CXX) $(CXXFLAGS) -o $@ inventory.cpp inventory_tests.cpp

test: inventory_tests
	./inventory_tests

clean:
	rm -f inventory_tests

.PHONY: test clean
