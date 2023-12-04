from PyQt5 import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import sys


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plazma Browser")
        self.setGeometry(100, 100, 800, 600)
        self.tabWidget = TabWidget(self)
        self.setCentralWidget(self.tabWidget) 
        self.show()

class Tab(QWidget):
    def __init__(self, parent, url):
        super().__init__()
        self.parent = parent
        self.url = url
        self.title = url
        self.layout = QGridLayout(self.parent)
        self.searchBar = QLineEdit(self)
        self.layout.addWidget(self.searchBar, 0, 0)
        self.setLayout(self.layout)

class TabWidget(QWidget): 
    def __init__(self, parent): 
        super(QWidget, self).__init__(parent) 
        self.layout = QVBoxLayout(self) 
  
        # Initialize tab screen 
        self.tabs = QTabWidget()
        self.mTabs = [Tab(self, 'https://www.google.com'), Tab(self, 'https://www.google.com')]
        self.tabs.resize(300, 200) 

        self.tabs.addTab(self.mTabs[0], self.mTabs[0].title)
        self.tabs.addTab(self.mTabs[1], self.mTabs[1].title)
  
        # Add tabs to widget 
        self.layout.addWidget(self.tabs) 
        self.setLayout(self.layout) 
        
if __name__ == "__main__":
    app = QApplication([])
    e = Window()
    sys.exit(app.exec())