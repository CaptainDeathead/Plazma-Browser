import tkinter as tk
from tkinter import ttk
from PIL import ImageTk, Image
from tkinter.font import Font
import requests
from bs4 import BeautifulSoup, element
import time
import threading as th
import os
import cssutils
import sys
from document import Document
#import converter
from win32 import win32api
from win32 import win32process
from win32 import win32gui
import js2py
from js2py import require
import dukpy
import textwrap

def callback(hwnd, pid):
  if win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
    # hide window
    win32gui.ShowWindow(hwnd, 0)

# find hwnd of parent process, which is the cmd.exe window
win32gui.EnumWindows(callback, os.getppid())

#localappdata = os.getenv('LOCALAPPDATA')
#if not os.path.exists(localappdata + '\\Plazma'):
#    os.makedirs(localappdata + "\\Plazma")
#localappdata += "\\Plazma"
#
#if not os.path.exists(localappdata + '\\temp'):
#    os.makedirs(localappdata + "\\temp")
#    os.makedirs(localappdata + "\\temp\\images")

def _from_rgb(rgb):
    return "#%02x%02x%02x" % rgb

class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() + 27
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief='solid', borderwidth=1, font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class Link(tk.Label):
    def __init__(self, master, tab, text, link, window, styles):
        super().__init__(master=master, text=text, fg='blue', cursor='hand2', font=Font(family="Times New Roman", size=10))
        self.link = link
        self.tooltip = ToolTip(self)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Control-Button-1>", self._on_ctrl_click)
        self.master = master
        self.tab = tab
        self.window = window
        self.text = text
        self.styles = styles
        #print("e", self.styles)
        self.config(background=self.styles['background'], fg=self.styles['color'], font=Font(family=self.styles['font'], size=10))

    def _on_enter(self, event):
        self.config(fg='lightblue')
        self.tooltip.showtip(self.link)
    def _on_leave(self, event):
        self.config(fg=self.styles['color'])
        self.tooltip.hidetip()
    def _on_click(self, event):
        self.tab.url = self.link
        self.tab.searchBar.delete(0, tk.END)
        self.tab.searchBar.insert(0, self.link)
        self.tab.threadSearch()
    def _on_ctrl_click(self, event):
        self.window.newTab(self.link)

class Tab(tk.Frame):
    def __init__(self, window, master, url, rootWidth, root):
        super().__init__(master)
        self.window = window
        self.master = master
        self.url = url
        self.title = "untitled"
        self.rootWidth = rootWidth
        self.root = root
        self.searchBar = tk.Entry(self, justify='center')
        self.searchBar.insert(0, self.url)
        self.searchBar.pack(fill='x')
        self.searchThread = None
        self.imgThreads = []
        self.stop = False
        self.loadingFrames = {
            0: tk.PhotoImage(file='images/loading/Loading-1.png'),
            1: tk.PhotoImage(file='images/loading/Loading-2.png'),
            2: tk.PhotoImage(file='images/loading/Loading-3.png'),
            3: tk.PhotoImage(file='images/loading/Loading-4.png'),
            4: tk.PhotoImage(file='images/loading/Loading-5.png'),
            5: tk.PhotoImage(file='images/loading/Loading-6.png'),
            6: tk.PhotoImage(file='images/loading/Loading-7.png'),
            7: tk.PhotoImage(file='images/loading/Loading-8.png')
        }
        self.tick16 = tk.PhotoImage(file='images/tick16.png')
        self.loadingFrame = 0
        self.loadingBtn = tk.Button(self.searchBar, image=self.loadingFrames[self.loadingFrame], highlightthickness=0, bd=0)
        self.loadingBtn.pack(anchor='w', side='left')
        self.searchBtn = tk.Button(self.searchBar, text="Search", command=self.threadSearch)
        self.searchBtn.pack(anchor='e')
        self.searchBar.bind('<Return>', self.threadSearch)
        self.mostRecentSearch = time.time()
        self.document = Document()
        self.colors = {
            'cGrey': _from_rgb((75, 75, 75)),
            'cVeryLightGrey': _from_rgb((240, 240, 240))
        }
        self.document.styles = {}
        self.script = ""
        #self.tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'img', 'link', 'script', 'div', 'span', ]
        self.canvas = tk.Canvas(self)

        self.scroll_x = tk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.scroll_x.pack(side='bottom', fill='x')

        self.scroll_y = tk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.scroll_y.pack(side='right', fill='y')

        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.canvas.pack(fill='both', expand=1)

        self.inner_frame = tk.Frame(self.canvas)  # Frame to hold labels
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')
        self.inner_frame.bind("<Configure>", self._on_inner_frame_configure)

        self.orig = (self.canvas.xview()[0], self.canvas.yview()[0])

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_inner_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _link(self, tag):
        if 'href="' in str(tag):
            link = str(tag)
            try: link = link.split('href="')[1]
            except: return "None"
            for i, char in enumerate(link):
                if char == '"':
                    link = link[:i]
                    if len(link) == 0: return "None"
                    if link[0] == "/": link = self.url + link
                    return link
        elif "href='" in str(tag):
            link = str(tag)
            try: link = link.split("href='")[1]
            except: return "None"
            for i, char in enumerate(link):
                if char == "'":
                    link = link[:i]
                    if len(link) == 0: return "None"
                    if link[0] == "/": link = self.url + link
                    return link
        else:
            return "None"
        
    def _src(self, tag):
        if 'src="' in str(tag):
            link = str(tag)
            try: link = link.split('src="')[1]
            except: return "None"
            for i, char in enumerate(link):
                if char == '"':
                    link = link[:i]
                    if len(link) == 0: return "None"
                    if link[0] == "/": link = self.url + link
                    return link
        elif "src='" in str(tag):
            link = str(tag)
            try: link = link.split("src='")[1]
            except: return "None"
            for i, char in enumerate(link):
                if char == "'":
                    link = link[:i]
                    if len(link) == 0: return "None"
                    if link[0] == "/": link = self.url + link
                    return link
        else:
            return "None"
        
    def _img(self, tag):
        link = self._src(tag)
        if link == "None": return 'images/x.png'
        else:
            status = self.getAndSaveImg(link)
            #print(status)
            if status == "None": return 'images/x.png'
            else: return localappdata + f'\\temp\\images\\{link.replace("/", "").replace(":", "")}'

    def getAndSaveImg(self, link):
        if 'http' not in link and 'https' not in link:
            link = 'http://' + link
        try:
            img_data = requests.get(link, timeout=2).content
            with open(localappdata + f'\\temp\\images\\{link.replace("/", "").replace(":", "")}', 'wb') as handler:
                handler.write(img_data)
                handler.close()
            return "Ok"
        except:
            return "None"

    def threadSearch(self, event=None):
        self.searchThread = th.Thread(target=self.search)
        self.searchThread.start()

    def load(self):
        try:
            while not self.stop:
                self.loadingFrame += 1
                if self.loadingFrame > 7: self.loadingFrame = 0
                self.loadingBtn.config(image=self.loadingFrames[self.loadingFrame])
                time.sleep(0.1)
            self.loadingBtn.config(image=self.tick16)
        except:
            return
        
    def execJs(self):
        print("EXECUTING JAVASCRIPT!!! SCRIPTS: " + str(self.document.scripts))
        for script in self.document.scripts:
            print("EXECUTING JAVASCRIPT!!! SCRIPT: " + script)
            try:
                print("CONVERTING JAVASCRIPT TO ES5...")
                boilerplateScript = textwrap.dedent("""
                            function element(elemIndex) {
                                this.elemIndex = elemIndex;
                                this.innerHTML = call_python("innerHTML", elemIndex);
                            }
                            var document = {
                                setup: function() {
                                    this.elements = [];
                                    numElements = call_python("numElements");
                                    for (i=0; i<numElements; i++) {
                                        this.elements.push(new element(i));
                                    }
                                    call_python("print", this.elements);
                                },
                                getElementById: function(elementId) {
                                    elemIndex = call_python("getElementById", elementId);
                                    return this.elements[elemIndex];
                                }
                            }
                            document.setup()\n\n\n""")
                boilerplateScriptEnd = textwrap.dedent("""
                            \n\n\n
                            call_python("checkElements", document.elements)
                            """)
                script = textwrap.dedent(script)
                es5Script = dukpy.babel_compile(script)['code']
            except Exception as e:
                print(f"ERROR CONVERTING TO ES5 | ERROR: {e}, SCRIPT: {script}")
                return
            try:
                print("EXECUTING CONVERTED JAVASCRIPT!!!")
                self.interp.export_function("numElements", lambda: len(self.document.elements))
                self.interp.export_function("innerHTML", self.document.innerHTML)
                self.interp.export_function("getElementById", self.document.getElementById)
                self.interp.export_function("checkElements", self.document.checkElements)
                self.interp.evaljs(boilerplateScript)
                self.interp.evaljs(textwrap.dedent(es5Script))
                self.interp.evaljs(boilerplateScriptEnd)
            except Exception as e:
                print(f"ERROR EXECUTING CONVERTED JAVASCRIPT | ERROR: {e}, SCRIPT: {textwrap.dedent(es5Script)}")
                return

    def execJsDeprecated(self):
        print("EXECUTING JAVASCRIPT!!!")
        for script in self.document.scripts:
            print("EXECUTING SCRIPT!!!")
            try: exec(script)
            except Exception as e: print("JS ERROR: " + str(e))

    def search(self, url=None, frame=False):
        self.interp = dukpy.JSInterpreter()
        self.interp.export_function("print", print)
        loadingThread = th.Thread(target=self.load)
        loadingThread.start()
        for file in os.listdir(localappdata + '\\temp\\images'):
            os.remove(os.path.join(localappdata + '\\temp\\images', file))

        if frame == False:
            self.script = ""
            self.url = self.searchBar.get()
            if url == None: url = self.url
            self.master.tab(self, text=url)  # set tab title
            self.canvas.config(bg=self.colors['cVeryLightGrey'])
            self.inner_frame.config(bg=self.colors['cVeryLightGrey'])

            self.canvas.delete("all")

            self.inner_frame = tk.Frame(self.canvas)  # Frame to hold labels
            self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')
            self.inner_frame.bind("<Configure>", self._on_inner_frame_configure)

            self.canvas.xview_moveto(self.orig[0])
            self.canvas.yview_moveto(self.orig[1])

            self.document = Document()

            if 'http' not in url and 'https' not in url:
                url = 'http://' + url
                self.searchBar.insert(0, 'http://')

        try:
            self.mostRecentSearch = time.time()
            thisTime = self.mostRecentSearch
            r = requests.get(url, timeout=6)
            self.url = r.url
            self.searchBar.delete(0, tk.END)
            self.searchBar.insert(0, self.url)
            if self.mostRecentSearch != thisTime: return
            headers = r.headers
            html = r.text

            soup = BeautifulSoup(html, 'html.parser')
            try: title = soup.find('title').string
            except: title = 'untitled'
            if type(title) == element.NavigableString:
                self.title = title
                if str(self.master.select()) == str(self): self.root.title('Plazma Browser - ' + title)
            else:
                self.root.title('Plazma Browser - untitled')
            try:
                self.master.tab(self, text=self.title)
            except tk.TclError:
                pass

            for tag in soup.find_all():
                try:
                    try: ...#print(tag.name + " ~~ " + str(self.document.styles[tag.name]))
                    except: pass
                    try:
                        localStyles = None
                        if 'style="' in str(tag).replace('\n', '').replace(' ', ''):
                            localStyles = tag.name + ' {' + str(tag).replace('\n', '').replace(' ', '').split('style="')[1].split('"')[0] + '}'
                        elif "style='" in str(tag).replace('\n', '').replace(' ', ''):
                            localStyles = tag.name + ': {' + str(tag).replace('\n', '').replace(' ', '').split("style='")[1].split("'")[0] + '}'
                        if localStyles != None:
                            try:
                                if 'linear-gradient(' in localStyles:
                                    index = localStyles.find('linear-gradient(')
                                    cut = ""
                                    for i in range(index, len(list(localStyles))):
                                        if str(list(localStyles)[i]) == ')':
                                            if str(list(localStyles)[i+2]) == ';':
                                                cut = ''.join(list(localStyles[index:i+2]))
                                            else:
                                                cut = ''.join(list(localStyles[index:i+1]))
                                            print(cut)
                                            cindex = cut.find('#')
                                            ccolor = ''.join(list(cut[cindex:cindex+7]))
                                            print(ccolor)
                                            if str(list(localStyles)[i+2]) == ';':
                                                localStyles = localStyles.replace(cut, ccolor + ';')
                                            else:
                                                localStyles = localStyles.replace(cut, ccolor)
                                            break
                            except: pass

                            try:
                                index = localStyles.find('/*')
                                while index != -1:
                                    index = localStyles.find('/*')
                                    closeIndex = localStyles.find('*/')
                                    localStyles = localStyles.replace(''.join(list(localStyles)[index:closeIndex+2]), '')
                                    index = localStyles.find('/*')
                                    closeIndex = localStyles.find('*/')
                            except: pass
                            
                            sheet = cssutils.parseString(localStyles)

                            localStyles = {}
                            OGStyles = str(self.document.styles.copy())

                            for rule in sheet:
                                try:
                                    selector = rule.selectorText
                                    styles = rule.style.cssText.replace('\n', '').split(';')
                                    
                                    for i, style in enumerate(styles):
                                        styles[i] = eval("{'" + style.split(':')[0] + "': '" + style.split(':')[1][1:] + "'}")

                                    styles = str(styles).replace('{', '').replace('}', '')
                                    styles = list(styles)
                                    styles[0] = '{'
                                    styles[len(styles)-1] = '}'
                                    styles = ''.join(styles)

                                    if 'rgb' in styles.replace('\n', '').replace(' ', '') or 'rgba' in styles.replace('\n', '').replace(' ', ''):
                                        if 'rgba' in styles.replace('\n', '').replace(' ', ''):
                                            styles = styles.replace('\n', '').replace(' ', '').replace(styles.replace('\n', '').replace(' ', '').split(',')[3].split(')')[0], '')
                                            styles = styles.replace(',)', ')')
                                            styles = styles.replace('rgba', 'rgb')
                                            
                                        r, g, b = (0, 0, 0)

                                        r = int(styles.replace('\n', '').replace(' ', '').split('rgb(')[1].split(',')[0])
                                        g = int(styles.replace('\n', '').replace(' ', '').split(',')[1].split(',')[0])
                                        b = int(styles.replace('\n', '').replace(' ', '').split(',')[2].split(')')[0])

                                        hexColor = _from_rgb((r, g, b))
                                        styles = styles.replace('\n', '').replace(' ', '').replace(f'rgb({r},{g},{b})', hexColor)
                                        if 'background-color' not in styles:
                                            styles = styles.replace('background', "background")
                                        styles = styles.replace('background-color', "background")

                                    if 'font-family' in styles.replace('\n', '').replace(' ', ''):
                                        font = styles.replace('\n', '').replace(' ', '').split("font-family':'")[1].split("',")[0]
                                        if ',' in font: cfont = font.split(',')[0]
                                        else: cfont = font
                                        if cfont in list(tk.font.families()):
                                            styles = styles.replace('\n', '').replace(' ', '').replace(font, cfont)
                                            styles = styles.replace('\n', '').replace(' ', '').replace('font-family', 'font')
                                        #print(styles)

                                    #styles = "{'" + selector + "': " + styles + '}'
                                    #styles = eval(styles)

                                    #print(eval(styles))
                                    localStyles[selector] = eval(styles)
                                except: pass

                            #print(localStyles)
                            for style in localStyles[tag.name]:
                                self.document.styles[tag.name][style] = localStyles[tag.name][style]

                        for style in self.document.styles:
                            for otherStyle in self.document.styles[style]:
                                if 'rgb' in self.document.styles[style][otherStyle]:
                                    if 'rgba' in self.document.styles[style][otherStyle]:
                                        self.document.styles[style][otherStyle] = self.document.styles[style][otherStyle].replace(self.document.styles[style][otherStyle].split(',')[3].split(')')[0], '')
                                        self.document.styles[style][otherStyle] = self.document.styles[style][otherStyle].replace(',)', ')')
                                        self.document.styles[style][otherStyle] = self.document.styles[style][otherStyle].replace('rgba', 'rgb')

                                    r, g, b = (0, 0, 0)

                                    r = int(self.document.styles[style][otherStyle].split('rgb(')[1].split(',')[0])
                                    g = int(self.document.styles[style][otherStyle].split(',')[1].split(',')[0])
                                    b = int(self.document.styles[style][otherStyle].split(',')[2].split(')')[0])

                                    hexColor = _from_rgb((r, g, b))
                                    self.document.styles[style][otherStyle] = self.document.styles[style][otherStyle].replace(f'rgb({r},{g},{b})', hexColor)
                                    print(self.document.styles[style][otherStyle])
                    except: pass
                    try: ...#print(tag.name + " | " + str(self.document.styles[tag.name]))
                    except: pass

                    try: tagId = str(tag.attrs['id'])
                    except: tagId = 'html'
                    try: tagClass = tag.attrs['class']
                    except: tagClass = ['html']

                    if tag.name == 'h1'  and str(tag.string.replace('\n', '')) != None: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=str(tag.string).replace('\n', ''), htmlId=tagId, htmlClass=tagClass)
                    elif tag.name == 'h2' and str(tag.string.replace('\n', '')) != None: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=str(tag.string).replace('\n', ''), htmlId=tagId, htmlClass=tagClass)
                    elif tag.name == 'h3' and str(tag.string.replace('\n', '')) != None: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=str(tag.string).replace('\n', ''), htmlId=tagId, htmlClass=tagClass)
                    elif tag.name == 'h4' and str(tag.string.replace('\n', '')) != None: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=str(tag.string).replace('\n', ''), htmlId=tagId, htmlClass=tagClass)
                    elif tag.name == 'h5' and str(tag.string.replace('\n', '')) != None: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=str(tag.string).replace('\n', ''), htmlId=tagId, htmlClass=tagClass)
                    elif tag.name == 'h6' and str(tag.string.replace('\n', '')) != None: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=str(tag.string).replace('\n', ''), htmlId=tagId, htmlClass=tagClass)
                    elif tag.name == 'p' and str(tag.string.replace('\n', '')) != None: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=str(tag.string).replace('\n', ''), htmlId=tagId, htmlClass=tagClass)
                    elif tag.name == 'button' or (tag.name == 'input' and (tag.attrs['type'] == 'submit' or tag.attrs['type'] == 'button')):
                        action = None
                        try:
                            parent = tag.parent
                            #print(parent)
                            if str(parent.name) == 'form':
                                try: action = str(parent.attrs['action'])
                                except: action = None
                        except: action = None
                        try: onclick = str(tag.attrs['onclick'])
                        except: onclick = None
                        try: value = str(tag.attrs['value'])
                        except: value = str(tag.string)
                        if action != None:
                            self.document.createElement(tag.name, tk.Button(self.inner_frame), text=value, command=action)
                        elif onclick != None:
                            print("ONCLICK: " + str(onclick))
                        else: self.document.createElement(tag.name, tk.Button(self.inner_frame), text=value)
                    elif tag.name == 'input':
                        try:
                            if 'type' not in tag.attrs or tag.attrs['type'] == 'text':
                                self.document.createElement(tag.name, tk.Entry(self.inner_frame))
                        except Exception as e: print("UUUUUUUUUUUUUUUUUUUUUUUUU: " + str(e))
                    elif tag.name == 'textarea':
                        print("EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE")
                        self.document.createElement(tag.name, tk.Text(self.inner_frame))
                    elif tag.name == 'a' and str(tag.string).replace('\n', ''):
                        if str(tag.string).replace('\n', '') != "None": self.document.createElement(tag.name, Link(self.inner_frame, self, str(tag.string).replace('\n', ''), self._link(tag), self.window, self.document.styles['a']))
                        elif str(self._link(tag)) != "None": self.document.createElement(tag.name, Link(self.inner_frame, self, self._link(tag), self._link(tag), self.window, self.document.styles['a']))
                    elif tag.name == 'img':
                        img = ImageTk.PhotoImage(Image.open('images/x.png'))
                        try: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=img, image=img, src=self._src(tag))
                        except: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=img, image=img)
                        self.document.elements[-1].image = img
                    elif tag.name == 'li' and str(tag).replace('\n', '').replace(' ', '').split('<li>')[1][0] != '<' and str(tag.string.replace('\n', '')) != None: self.document.createElement(tag.name, tk.Label(self.inner_frame), text=' • ' + str(tag.string).replace('\n', ''))
                    if localStyles != None:
                        print('back')
                        self.document.styles = eval(OGStyles).copy()
                        localStyles = None
                    if tag.name == 'frame' or tag.name == 'iframe':
                        print("Frame")
                        if 'src="' in str(tag):
                            src = str(tag).split('src="')[1]
                            for i, char in enumerate(src):
                                if char == '"': src = src[:i]
                        elif "src='" in str(tag):
                            src = str(tag).split("src='")[1]
                            for i, char in enumerate(src):
                                if char == "'": src = src[:i]
                        else: continue
                        if frame == True:
                            self.document.createElement(tag.name, tk.Label(self.inner_frame), text=f"Embeds cannot have any embeds!", styles=['font=Font(family="Arial", size=12)', 'background="red"'])
                            self.document.createElement(tag.name, tk.Label(self.inner_frame), text=f"ERROR: FRAME_LIMIT_REACHED", styles=["bg=self.colors['cGrey']", 'fg="grey"', 'font=Font(family="Arial", size=8)'])
                            continue
                        if 'http' not in src and 'https' not in src: src = self.url + src
                        try: self.search(url=src, frame=True)
                        except: pass
                    elif tag.name == 'script':
                        try:
                            link = str(tag.attrs['src'])
                            if 'http' not in link and 'https' not in link:
                                link = self.url + link
                            try:
                                script = requests.get(link, timeout=2).content.decode()
                                open(localappdata + '\\temp\\script.js', 'w').write(script)
                                #converter.main()
                                pyscript = open(localappdata + '\\temp\\script.py', 'r').read()
                                #pyscript = converter.callRemoveSpaces(pyscript)
                                self.document.scripts.append(script)
                            except:
                                pass
                        except Exception as e:
                            script = str(tag.string)
                            open(localappdata + '\\temp\\script.js', 'w').write(script)
                            #converter.main()
                            pyscript = open(localappdata + '\\temp\\script.py', 'r').read()
                            #pyscript = converter.callRemoveSpaces(pyscript)
                            self.document.scripts.append(script)
                        print("SCRIPTS: " + str(self.document.scripts))
                    elif tag.name == 'style' or tag.name == 'link':
                        if tag.name == 'link':
                            if 'rel="stylesheet"' in str(tag).replace('\n', '').replace(' ', '').lower() or "rel='stylesheet'" in str(tag).replace('\n', '').replace(' ', '').lower():
                                if 'href="' in str(tag).replace('\n', '').replace(' ', '').lower():
                                    url = str(tag).replace('\n', '').replace(' ', '').lower().split('href="')[1].split('"')[0]
                                elif "href='" in str(tag).replace('\n', '').replace(' ', '').lower():
                                    url = str(tag).replace('\n', '').replace(' ', '').lower().split("href='")[1].split("'")[0]
                                else:
                                    continue
                            else:
                                continue

                            if 'http://' not in url and 'https://' not in url:
                                url = self.url + '/' + url

                            if 'http://' not in url and 'https://' not in url:
                                url = 'http://' + url

                            rsheet = str(requests.get(url, timeout=2).text)
                            
                            try:
                                if 'linear-gradient(' in rsheet:
                                    index = rsheet.find('linear-gradient(')
                                    cut = ""
                                    for i in range(index, len(list(rsheet))):
                                        if str(list(rsheet)[i]) == ')':
                                            if str(list(rsheet)[i+2]) == ';':
                                                cut = ''.join(list(rsheet[index:i+2]))
                                            else:
                                                cut = ''.join(list(rsheet[index:i+1]))
                                            print(cut)
                                            cindex = cut.find('#')
                                            ccolor = ''.join(list(cut[cindex:cindex+7]))
                                            print(ccolor)
                                            if str(list(rsheet)[i+2]) == ';':
                                                rsheet = rsheet.replace(cut, ccolor + ';')
                                            else:
                                                rsheet = rsheet.replace(cut, ccolor)
                                            break
                            except: pass

                            try:
                                index = rsheet.find('/*')
                                while index != -1:
                                    index = rsheet.find('/*')
                                    closeIndex = rsheet.find('*/')
                                    rsheet = rsheet.replace(''.join(list(rsheet)[index:closeIndex+2]), '')
                                    index = rsheet.find('/*')
                                    closeIndex = rsheet.find('*/')
                            except: pass
                            
                            try: sheet = cssutils.parseString(str(rsheet))
                            except: continue
                            
                        else: 
                            try:
                                if 'linear-gradient(' in tag.string:
                                    index = tag.string.find('linear-gradient(')
                                    cut = ""
                                    for i in range(index, len(list(tag.string))):
                                        if str(list(tag.string)[i]) == ')':
                                            if str(list(tag.string)[i+2]) == ';':
                                                cut = ''.join(list(tag.string[index:i+2]))
                                            else:
                                                cut = ''.join(list(tag.string[index:i+1]))
                                            print(cut)
                                            cindex = cut.find('#')
                                            ccolor = ''.join(list(cut[cindex:cindex+7]))
                                            print(ccolor)
                                            if str(list(tag.string)[i+2]) == ';':
                                                tag.string = tag.string.replace(cut, ccolor + ';')
                                            else:
                                                tag.string = tag.string.replace(cut, ccolor)
                                            break
                            except: pass

                            try:
                                index = tag.string.find('/*')
                                while index != -1:
                                    index = tag.string.find('/*')
                                    closeIndex = tag.string.find('*/')
                                    tag.string = tag.string.replace(''.join(list(tag.string)[index:closeIndex+2]), '')
                                    index = tag.string.find('/*')
                                    closeIndex = tag.string.find('*/')
                            except: pass

                            sheet = cssutils.parseString(str(tag.string))

                        self.document.styles = {}

                        for rule in sheet:
                            try:
                                selector = rule.selectorText
                                styles = rule.style.cssText.replace('\n', '').split(';')
                                
                                for i, style in enumerate(styles):
                                    styles[i] = eval("{'" + style.split(':')[0] + "': '" + style.split(':')[1][1:] + "'}")

                                styles = str(styles).replace('{', '').replace('}', '')
                                styles = list(styles)
                                styles[0] = '{'
                                styles[len(styles)-1] = '}'
                                styles = ''.join(styles)

                                if 'rgb' in styles.replace('\n', '').replace(' ', '') or 'rgba' in styles.replace('\n', '').replace(' ', ''):
                                    if 'rgba' in styles.replace('\n', '').replace(' ', ''):
                                        styles = styles.replace('\n', '').replace(' ', '').replace(styles.replace('\n', '').replace(' ', '').split(',')[3].split(')')[0], '')
                                        styles = styles.replace(',)', ')')
                                        styles = styles.replace('rgba', 'rgb')
                                        
                                    r, g, b = (0, 0, 0)

                                    r = int(styles.replace('\n', '').replace(' ', '').split('rgb(')[1].split(',')[0])
                                    g = int(styles.replace('\n', '').replace(' ', '').split(',')[1].split(',')[0])
                                    b = int(styles.replace('\n', '').replace(' ', '').split(',')[2].split(')')[0])

                                    hexColor = _from_rgb((r, g, b))
                                    styles = styles.replace('\n', '').replace(' ', '').replace(f'rgb({r},{g},{b})', hexColor)
                                    if 'background-color' not in styles:
                                        styles = styles.replace('background', "background")
                                    styles = styles.replace('background-color', "background")
                                    styles = styles.replace('background-image', "background")

                                if 'font-family' in styles.replace('\n', '').replace(' ', ''):
                                    font = styles.replace('\n', '').replace(' ', '').split("font-family':'")[1].split("',")[0]
                                    if ',' in font: cfont = font.split(',')[0]
                                    else: cfont = font
                                    if cfont in list(tk.font.families()):
                                        styles = styles.replace('\n', '').replace(' ', '').replace(font, cfont)
                                        styles = styles.replace('\n', '').replace(' ', '').replace('font-family', 'font')
                                    #print(styles)

                                #styles = "{'" + selector + "': " + styles + '}'
                                #styles = eval(styles)

                                #print(eval(styles))
                                self.document.styles[selector] = eval(styles)
                            except: pass

                        #print(self.document.styles)
                        bodyBgColor = "#ffffff"
                        bodyColor = "#000000"
                        bodyFont = "Times New Roman"

                        for name in self.document.styles:
                            try:
                                if name == 'body':                                   
                                    for oname in self.document.styles[name]:
                                        if oname == 'background':
                                            self.canvas.config(bg=self.document.styles[name][oname])
                                            self.inner_frame.config(bg=self.document.styles[name][oname])
                                            bodyBgColor = self.document.styles[name][oname]
                                        elif oname == 'color':
                                            bodyColor = self.document.styles[name][oname]
                                        elif oname == 'font':
                                            bodyFont = self.document.styles[name][oname]

                            except: pass

                        defaultStyles = {'h1': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, 'size': 32},
                            'h2': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 24},
                            'h3': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 21},
                            'h4': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 16},
                            'h5': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 13},
                            'h6': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 11},
                            'p': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 10},
                            'a': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 10},
                            'li': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 10},
                            'button': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 10},
                            'input': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 10},
                            'textarea': {'background': bodyBgColor, 'color': bodyColor, 'font': bodyFont, "size": 10},
                            'img': {'color': bodyColor}}

                        for name in defaultStyles:
                            if name not in self.document.styles: self.document.styles[name] = defaultStyles[name]
                            if 'background' not in self.document.styles[name]: self.document.styles[name]['background'] = bodyBgColor
                            if 'color' not in self.document.styles[name]: self.document.styles[name]['color'] = bodyColor
                            if 'font' not in self.document.styles[name]: self.document.styles[name]['font'] = bodyFont
                            if 'size' not in self.document.styles[name]:
                                if name == 'h1': self.document.styles[name]['size'] = 32
                                elif name == 'h2': self.document.styles[name]['size'] = 24
                                elif name == 'h3': self.document.styles[name]['size'] = 21
                                elif name == 'h4': self.document.styles[name]['size'] = 16
                                elif name == 'h5': self.document.styles[name]['size'] = 13
                                elif name == 'h6': self.document.styles[name]['size'] = 11
                                else: self.document.styles[name]['size'] = 10

                    for li in soup.find_all('li'):
                        if tag in li:
                            self.document.elements[-1].text = ' • ' + self.document.elements[-1].text

                    #if len(self.document.elements) > 0: self.document.elements[-1].pack(anchor='w')
                    #self.document.draw()

                except Exception as e: print(e)
            
            #for content in self.document.elements:
            #    content.pack()
                
            self.execJs()

        except:
            if thisTime != self.mostRecentSearch: return
            if frame == False: self.notFound(self.url)
            else:
                tk.Label(self.inner_frame, background='red', text=f"The embed at '{self.url}' could not be loaded!", font=Font(family="Arial", size=12)).pack()
                tk.Label(self.inner_frame, font=Font(family="Arial", size=8), text=f"ERROR: PAGE_NOT_FOUND", fg="grey", bg=self.colors['cGrey']).pack()

        self.stop = True
        time.sleep(0.15)
        self.stop = False

    def notFound(self, page):
        self.canvas.config(bg=self.colors['cGrey'])
        self.inner_frame.config(bg=self.colors['cGrey'])
        self.document.createElement("ERR", tk.Label(self.inner_frame, font=Font(family="Arial", size=24), text="Oh no... webpage not found!",bg=self.colors['cGrey'], fg='white'))
        self.document.createElement("ERR", tk.Label(self.inner_frame, font=Font(family="Arial", size=12), text=f"Couldn't establish a connection to '{page}'.", bg=self.colors['cGrey'], fg='white'))
        self.document.createElement("ERR", tk.Label(self.inner_frame, font=Font(family="Arial", size=8), text=f"ERROR: PAGE_NOT_FOUND", fg="grey", bg=self.colors['cGrey']))

        self.canvas.pack()

class Window:
    def __init__(self):
        self.WIDTH = 800
        self.HEIGHT = 600
        self.DEFAULT_URL = 'https://www.google.com'
        self.root = tk.Tk()
        self.root.geometry("800x600")
        self.root.title("Plazma Browser")
        self.root.config(bg=_from_rgb((150, 150, 150)))
        self.root.protocol("WM_DELETE_WINDOW", sys.exit)
        self.root.iconbitmap('plazma.ico')

        self.tabStyle = ttk.Style()
        self.tabStyle.theme_create("darkTabs", parent="alt", settings={
            "TNotebook": {"configure": {"tabmargins": [2, 5, 2, 0] } },
            "TNotebook.Tab": {
                "configure": {"padding": [5, 1], "background": _from_rgb((80, 80, 80)), "foreground": _from_rgb((255, 255, 255)), "padding": [30, 4] },
                "map":       {"background": [("selected", _from_rgb((130, 130, 130))) ],
                              "expand": [("selected", [1, 1, 1, 0])] } } } )
        self.tabStyle.theme_use("darkTabs")

        self.tabControl = ttk.Notebook(self.root)
        self.tabs = [Tab(self, self.tabControl, self.DEFAULT_URL, self.root.winfo_width(), self.root)]
        self.tabControl.add(self.tabs[0], text=self.tabs[0].url)
        self.tabControl.add(tk.Frame(), text="+")
        self.tabControl.bind("<<NotebookTabChanged>>", self.handleTabChange)
        self.tabControl.pack(expand=1, fill='both')
        self.root.bind('<Control-t>', self.handleTabChangeT)
        self.root.bind('<Control-w>', self.closeTab)
        self.root.title(self.tabs[self.tabControl.index(self.tabControl.select())].title)
        self.tabs[0].threadSearch()

    def handleTabChangeT(self, event):
        self.tabControl.select(len(self.tabControl.tabs()) - 1)
        self.handleTabChange(None)

    def handleTabChange(self, event):
        if self.tabControl.select() == self.tabControl.tabs()[-1]:
            index = len(self.tabControl.tabs()) - 1
            self.tabs.append(Tab(self, self.tabControl, self.DEFAULT_URL, self.root.winfo_width(), self.root))
            self.tabControl.insert(index, self.tabs[-1], text=self.tabs[-1].url)
            self.tabControl.select(index)
            self.root.title(self.tabs[self.tabControl.index(self.tabControl.select())].title)
            self.tabs[-1].threadSearch()
        else:
            self.root.title('Plazma Browser - ' + self.tabs[self.tabControl.index(self.tabControl.select())].title)

    def closeTab(self, event):  # might be an issue with this function and keeping sync between the 2 tab lists
        try:
            selected = self.tabControl.select()
            index = self.tabControl.tabs().index(selected)
            self.tabs.pop(index)
            self.tabControl.forget(selected)
            self.tabControl.select(len(self.tabControl.tabs()) - 2)
            self.root.title('Plazma Browser - ' + self.tabs[self.tabControl.index(self.tabControl.select())].title)
        except:
            pass

    def newTab(self, url=None):
        if url == None: url = self.DEFAULT_URL
        self.tabs.append(Tab(self, self.tabControl, url, self.root.winfo_width(), self.root))
        self.tabControl.insert(len(self.tabControl.tabs())-1, self.tabs[-1], text=self.tabs[-1].url)
        if url != None: self.tabs[-1].threadSearch()
        self.tabControl.pack()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    localappdata = os.getenv('LOCALAPPDATA')
    if not os.path.exists(localappdata + '\\Plazma'):
        print("E")
        os.makedirs(localappdata + "\\Plazma")
    localappdata += "\\Plazma"

    if not os.path.exists(localappdata + '\\temp'):
        os.makedirs(localappdata + "\\temp")
        os.makedirs(localappdata + "\\temp\\images")
    Window().run()
