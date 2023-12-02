all:
	g++ -o build main.cpp `sdl2-config --cflags --libs`
	./build