import tkinter as tk
from tkinter import ttk
import requests
from bs4 import BeautifulSoup
import time

class Tab(ttk.Frame):
    def __init__(self, master, url, rootWidth):
        super().__init__(master)
        self.master = master
        self.url = url
        self.title = "Plazma Browser - untitled"
        self.rootWidth = rootWidth
        self.searchBar = tk.Entry(self, justify='center')
        self.searchBar.insert(0, self.url)
        self.searchBar.pack(fill='x')
        self.searchBtn = tk.Button(self.searchBar, text="Search", command=self.search)
        self.searchBtn.pack(anchor='e')

    def search(self):
        self.url = self.searchBar.get()
        self.master.tab(self, text=self.url)
        
class Window:
    def __init__(self):
        self.WIDTH = 800
        self.HEIGHT = 600
        self.DEFAULT_URL = 'https://www.google.com'
        self.root = tk.Tk()
        self.root.geometry("800x600")
        self.root.title("Plazma Browser")
        self.tabControl = ttk.Notebook(self.root)
        self.tabs = [Tab(self.tabControl, self.DEFAULT_URL, self.root.winfo_width())]
        self.tabControl.add(self.tabs[0], text=self.tabs[0].url)
        self.tabControl.add(tk.Frame(), text="+")
        self.tabControl.bind("<<NotebookTabChanged>>", self.handleTabChange)
        self.tabControl.pack(expand=1, fill='both')
        self.root.bind('<Control-t>', self.handleTabChangeT)
        self.root.bind('<Control-w>', self.closeTab)
        self.root.title(self.tabs[self.tabControl.index(self.tabControl.select())].title)

    def handleTabChangeT(self, event):
        self.tabControl.select(len(self.tabControl.tabs())-1)
        self.handleTabChange(None)

    def handleTabChange(self, event):
        if self.tabControl.select() == self.tabControl.tabs()[-1]:
            index = len(self.tabControl.tabs())-1
            self.tabs.append(Tab(self.tabControl, self.DEFAULT_URL, self.root.winfo_width()))
            self.tabControl.insert(index, self.tabs[-1], text=self.tabs[-1].url)
            self.tabControl.select(index)
            self.root.title(self.tabs[self.tabControl.index(self.tabControl.select())].title)

    def closeTab(self, event): #  might be an issue with this function and keeping sync between the 2 tab lists
        try:
            selected = self.tabControl.select()
            index = self.tabControl.tabs().index(selected)
            self.tabs.pop(index)
            self.tabControl.forget(selected)
            self.tabControl.select(len(self.tabControl.tabs())-2)
            self.root.title(self.tabs[self.tabControl.index(self.tabControl.select())].title)
        except: pass

    def newTab(self):
        self.tabs.append(Tab(self.tabControl, self.DEFAULT_URL))
        self.tabControl.add(self.tabs[-1], text=self.tabs[-1].url)
        self.tabControl.pack()

    def draw(self):
        ...

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    Window().run()