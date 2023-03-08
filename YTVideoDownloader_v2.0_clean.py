import os
import socket
import requests
import webbrowser
from PIL import Image
from io import BytesIO
from pathlib import Path
from tkinter import Menu
from pytube import YouTube
from random import randint
from customtkinter import *
from threading import Thread
from pytube.streams import request

set_appearance_mode('dark')
set_default_color_theme('blue')

def has_internet():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return False if ip_address == '127.0.0.1' else True

def resolve_filename(filename:str):
    escape = '<>:/|?*\"\\'
    resolved = ''
    for i in filename:
        resolved += '_' if i in escape else i
    return resolved

class YOUTUBE:
    def __init__(self, url:str) -> None:
        self.url = url
        self.filesize = None #store the filesize
        self.previousprogress = 0 #counting download progress
        self.CANCEL_DOWNLOAD = False
    
    def is_valid_url(self, url=''):
        #simplest youtube url validation
        if url:
            if ('youtu.be/' in url) or ('youtube.com/' in url):
                return True
        elif self.url:
            if ('youtu.be/' in self.url) or ('youtube.com/' in self.url):
                return True
        return False
    
    def get_info(self) -> dict:
        try:
            infoLabel.pack_forget()
            if has_internet():
                if self.is_valid_url(self.url):
                    ytObj = YouTube(self.url)
                    title = ytObj.title #video title
                    duration = round(ytObj.length / 60, 2) #video duration in minutes

                    th_url = ytObj.thumbnail_url #video thumbnail url
                    with requests.get(th_url, stream=True) as response:
                        image_data = response.content #raw image data
                    img_bytes = Image.open(BytesIO(image_data)) #raw image data to bytes
                    image = img_bytes.resize((854,480), Image.LANCZOS) #image bytes to image

                    audio = ytObj.streams.get_audio_only().itag #only audio's itag int

                    response = ytObj.streams.filter(progressive=True, file_extension='mp4') #all info of response
                    vid_options = {} #store itag and resolution
                    for idx, vid in enumerate(response):
                        temp = {
                            'resolution': vid.resolution,
                            'itag': vid.itag}
                        vid_options[f'quality_{idx}'] = temp

                    # vid_options look like this
                    # vid_options = {
                    #     'quality_0': {'itag': 140, 'resolution': '360p'},
                    #     'quality_1': {'itag': 144, 'resolution': '720p'}}
                    
                    video_info = {
                        'title': title,
                        'duration': duration,
                        'image': image,
                        'audio_itag': audio,
                        'video': vid_options
                    }
                    return video_info

                infoLabel.configure(text='Error: Invalid url')
                infoLabel.pack()
                return False
            else:
                infoLabel.configure(text='Error: No Internet Access! \nPlease, reconnect and try again.')
                infoLabel.pack()
                return False
        except Exception as e:
            infoLabel.configure(text='Error: Something went wrong! \nTry again')
            infoLabel.pack()
            return False
    
    def latest_file(self, path):
        files = os.listdir(path)
        paths = [os.path.join(path, basename) for basename in files]
        return max(paths, key=os.path.getmtime)
    
    #download manually for adding download_cancel option
    def write_into_file(self, url, file_path):
            try:
                #open the given file path with filename and ext
                with open(file_path, "wb") as file:
                    #set download mb as 0 on download button click
                    downloaded_mb = 0
                    
                    for chunk in request.stream(url, timeout=None, max_retries=0):
                        if self.CANCEL_DOWNLOAD:
                            file.close()
                            try:
                                cloud_filename = self.video_title
                                local_file_path = self.latest_file(self.download_dir)
                                local_filename = os.path.basename(local_file_path)

                                if local_filename == cloud_filename:
                                    os.remove(local_file_path)

                                    #show cancellation msg to end user
                                    cancel_btn.configure(text='Cancelled')
                                    infoLabel.configure(text=f'Download cancelled!')
                            except Exception as e:
                                pass
                            self.CANCEL_DOWNLOAD = False #set CANEL=False to prevent automatically cancel next download
                            return 

                        file.write(chunk)
                        downloaded_mb += (len(chunk) / 1024) / 1024
                        percentage = round((downloaded_mb / self.filesize), 2)
                        progressBar.set(percentage) #progressBar takes 0.0 to 1
                        infoLabel.configure(text='Downloading: {}MB / {}MB'.format(round(downloaded_mb, 2), self.filesize))
                

                #when download complete
                infoLabel.configure(text=f'Download Complete! \nPath: {os.path.dirname(file_path)}', cursor='hand2')
                infoLabel.bind("<Button-1>", lambda a: open_in_fileexplorer(file_path))
                cancel_btn.pack_forget()
                return True
            except Exception as e:
                infoLabel.configure(text=f'Error: {e}')
                return False

    def download(self, itag=None, download_to=None, audio_only=False):
        try:
            if has_internet():
                if itag and download_to:
                    #downloading progress
                    self.previousprogress = 0
                    def on_download_progress(stream, chunk, bytes_remaining):
                        total_size = self.filesize_bytes
                        bytes_downloaded = total_size - bytes_remaining
                        liveprogress = int(bytes_downloaded / total_size * 100)
                        
                        if liveprogress > self.previousprogress:
                            self.previousprogress = liveprogress
                            progressBar.set(liveprogress / 100) #progressBar takes 0.0 to 1, eg: (liveprogress=45 / 100) = 0.45
                            infoLabel.configure(text='Downloading: {:.2f}MB / {}MB'.format((bytes_downloaded/1024)/1024, self.filesize))
                    
                    def on_complete(stream, path):
                        progressBar.set(1)
                        infoLabel.configure(text=f'Download Complete! \nPath: {download_to}')

                    #initial youtube instance
                    youtubeObj = YouTube(self.url, on_progress_callback=on_download_progress, on_complete_callback=on_complete)
                    video = youtubeObj.streams.get_by_itag(itag=itag)
                    
                    self.filesize_bytes = video.filesize
                    self.filesize = round(video.filesize_mb, 2)
                    infoLabel.configure(text=f'Downloading: 0.0MB / {self.filesize}MB')
                    progressBar.set(0.0)
                    progressBar.pack(pady=10)
                    cancel_btn.pack()

                    #if file size is less than 9 mb then hide cancel btn
                    #because chunk size is 9 mb, on_progress wont call on less than 9 mb file
                    if self.filesize > 9:
                        cancel_btn.configure(text='Cancel', state='normal')
                        cancel_btn.pack()
                    else: cancel_btn.pack_forget()
                    
                    #resolving (delete escape seq like: <>:"\/| etc) file name to avoid error creating file in windows
                    fileName = resolve_filename(video.title)
                    if audio_only:
                        fileName += '.mp3'
                    else:
                        fileName += '.mp4'
                    
                    #these two variable for download_cancelation
                    self.video_title = fileName
                    self.download_dir = download_to

                    #create absolute file path like, C:/User/<user>/Downloads/filename.extention
                    abs_file_path = os.path.join(download_to, fileName)
                    abs_file_path = os.path.abspath(abs_file_path)
                    if not video.exists_at_path(abs_file_path):
                        # video.download(download_to, filename=fileName)
                        self.write_into_file(video.url, abs_file_path)
                    else:
                        #if file already exists
                        progressBar.set(1)
                        infoLabel.configure(text=f'This file already exists in :\n{download_to}', cursor='hand2')
                        infoLabel.bind("<Button-1>", lambda a: open_in_fileexplorer(abs_file_path))
                        cancel_btn.pack_forget()

                    #rename file mp4 to mp3 manually
                    # if audio_only:
                    #     file_path = self.latest_file(download_to)
                    #     src_filename = os.path.basename(file_path)
                    #     mp3File_path = file_path.split('.mp4')[0] + '.mp3'
                    #     title_prefix = str(youtubeObj.title).split(' ')[0]
                    #     if src_filename.startswith(title_prefix) and src_filename.endswith('.mp4'):
                    #         try: os.rename(file_path, mp3File_path) #return WinError 183 if same file already exists
                    #         except: pass
                    
                else:
                    infoLabel.configure(text='Error: Video resolution or download folder not provided')
            else:
                infoLabel.configure(text='Error: No Internet Access! \nPlease, reconnect and try again.')
        except Exception as e:
            infoLabel.configure(text='Error: Something went wrong \nTry againg!')
            progressBar.pack_forget()


class App(CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #file download directory like, C/User/<username>/Downloads
        self.download_dir = self.get_default_dir()

        self.tips = [
            'Do not close the window while downloading, but you can minimize',
            'Usually download audio takes more time than expected, give it some time.',
            'You can download audio also.',
            'You can select any directory to save the file in it.',
            'If you do not select any folder then it will save to your Downloads folder.',
            'You can download from multiple resolution.',
            'Downloading progress bar does not work on less than 10 mb file.',
            'Cancel button works if you are downloading a file greater than 10 mb.'
        ]

        #meta data of window
        self.title('YouTube Video Downloader')
        self.iconbitmap('logo.ico')

        w_height = self.winfo_screenheight()-75
        w_width = 500
        x_coordinates = self.winfo_screenwidth() - (w_width+10)
        y_coordinates = 1
        winsize_and_coordinates = f"{w_width}x{w_height}+{x_coordinates}+{y_coordinates}"
        self.geometry(winsize_and_coordinates)

        #open developer github acc on default browser
        def callback(url):
            webbrowser.open_new(url)
        self.copyright = CTkLabel(self, text='Developer: @github:anwar-hasaan', cursor="hand2", text_color='skyblue', font=("san-sarif", 13, "bold"))
        self.copyright.place(relx=0.48, rely=0.07, anchor='center')
        self.copyright.bind("<Button-1>", lambda e: callback("https://github.com/anwar-hasaan"))

        #title of this application
        self.title = CTkLabel(self, text='YouTube Video Downloader', text_color='skyblue', font=("san-sarif", 24, "bold"))
        self.title.pack(padx=10, pady=15)
        
        #information label
        global infoLabel
        infoLabel = CTkLabel(self, text='', text_color='skyblue', font=("san-sarif", 16, "normal"))

        # //////////////////////////////////////////////////////////////////////////////
        #Context menu to perform copy, paste, cut and select all
        the_menu = Menu(self, tearoff=0)
        the_menu.add_command(label="Cut")
        the_menu.add_command(label="Copy")
        the_menu.add_command(label="Paste")
        the_menu.add_separator()
        the_menu.add_command(label="Select all")

        def show_textmenu(event):
            entry = event.widget
            entry.focus()
            the_menu.tk.call("tk_popup", the_menu, event.x_root, event.y_root)

            the_menu.entryconfigure("Cut",command=lambda: entry.event_generate("<<Cut>>"))
            the_menu.entryconfigure("Copy",command=lambda: entry.event_generate("<<Copy>>"))
            the_menu.entryconfigure("Paste",command=lambda: entry.event_generate("<<Paste>>"))
            the_menu.entryconfigure("Select all",command=lambda: entry.select_range(0, 'end'))
        
        self.bind_class("Entry", "<Button-3><ButtonRelease-3>", show_textmenu)
        # //////////////////////////////////////////////////////////////////////////////

        #entry box to get the youtube video url
        self.link = CTkEntry(self, width=350, height=40, placeholder_text='Paste the YouTube video link here')
        self.link.pack(pady=10)

        #gather all info of the video and display to end user
        def get_vid_info(function):
            Thread(target=function).start()
        self.get_video = CTkButton(self, text='Get Video', command=lambda: get_vid_info(self.get_video_info))
        self.get_video.pack(padx=5, pady=2)

        #downloading progressbar
        global progressBar
        progressBar = CTkProgressBar(self, width=350, height=25, corner_radius=3)

        #download cancellation button, works if downloading a file >10 mb
        def cancel_download():
            self.youtubeObj.CANCEL_DOWNLOAD = True
            if self.youtubeObj.CANCEL_DOWNLOAD:
                cancel_btn.configure(text='Canceling...', state='disabled')
        global cancel_btn
        cancel_btn = CTkButton(self, text='Cancel', width=80, height=30, command=cancel_download)
        
        #thumbnail of the video
        self.thumbnail = CTkLabel(self, text='', wraplength=350, font=("san-sarif", 16, "bold")) #image=image
        
        #get the filesize of selected resolution
        def file_size(function, choice):
            Thread(target=function, args=(choice,)).start()
        self.resolution = CTkOptionMenu(self, width=350, height=40, values=['Select Type and Quality'], command=lambda choice: file_size(self.show_file_size, choice))
        
        self.dir_label = CTkLabel(self, text=f'Download To:\n{self.download_dir}')

        #ask download directory from end user
        self.dir_btn = CTkButton(self, text='Select Download Folder', width=350, height=40, command=self.get_download_dir)

        #hit the download button
        def dowbload(function):
            Thread(target=function).start()
        self.download_btn = CTkButton(self, text='Download', command=lambda: dowbload(self.startDownload))

        #show all the tips to the end user
        self.helpText = CTkLabel(self, text=f'Tips : {self.tips[randint(0, len(self.tips)-1)]}', font=("san-sarif", 13, "bold"))
        self.helpText.place(relx=0.50, rely=0.98, anchor='center')

    #show file size of selected resolution
    def show_file_size(self, choice):
        url = self.link.get()
        itag = int(choice.split(':')[-1])
        
        #check if device has internet connection
        if has_internet():
            infoLabel.configure(text=f'File Size: Loading...', cursor='arrow')
            infoLabel.unbind("<Button-1>")
            infoLabel.pack()
            self.resolution.configure(state='disabled')
            self.download_btn.configure(state='disabled')
            cancel_btn.pack_forget()
            progressBar.pack_forget()

            #getting file size of selected itag
            youtubeObj = YouTube(url=url)
            video = youtubeObj.streams.get_by_itag(itag)
            size = round((video.filesize / 1024) / 1024, 2)
            
            #display file size using label
            self.resolution.configure(state='normal')
            infoLabel.configure(text=f'File Size: {size} MB')
            self.download_btn.configure(state='normal')
        else:
            infoLabel.configure(text='Error: No Internet Access! \nPlease reconnect and try again')

    #display download directory
    global open_in_fileexplorer
    def open_in_fileexplorer(file_path):

        #making function to call as a thread
        def file_open_thread(file_path):
            try:
                if not file_path:
                    return

                #getting the absolute path to avoid err
                #without abspath in some case it only open the file explorer home page
                file_path = os.path.abspath(file_path)
                if os.name == 'nt':
                    if os.path.isfile(file_path):
                        os.popen(f'explorer /select,"{file_path}"')

                    elif os.path.isdir(file_path):
                        os.startfile(file_path, 'explore')
                    
                    else:
                        dir = os.path.dirname(file_path)
                        if os.path.exists(dir):
                            os.startfile(dir, 'explore')
            except Exception as e:
                pass

        #start thread to run in background
        Thread(target=file_open_thread, args=(file_path, )).start()

    def get_video_info(self):
        #hide all component after provide url and clicked get_video
        infoLabel.configure(cursor='arrow')
        infoLabel.unbind("<Button-1>")
        infoLabel.pack_forget()

        self.thumbnail.pack_forget()
        self.resolution.pack_forget()
        self.dir_label.pack_forget()
        self.dir_btn.pack_forget()
        self.download_btn.pack_forget()
        progressBar.pack_forget()
        cancel_btn.pack_forget()

        try:
            url = self.link.get() #get the url from CTkEntry
            self.youtubeObj = YOUTUBE(url) #initiate the YOUTUBE class
            
            #validating the given url is a youtube video or not
            if self.youtubeObj.is_valid_url():
                self.get_video.configure(text='Please Wait...', state='disabled')

                video_info = self.youtubeObj.get_info() #get all info of given video url
                
                #if return value is empty then return to end user
                if not video_info:
                    self.get_video.configure(text='Get Video', state='normal')
                    return False

                #set the thumbnail image
                videoTitle = video_info['title']
                duration = video_info['duration']

                thumbnail = CTkImage(light_image=video_info['image'], size=(350, 200))
                self.thumbnail.configure(image=thumbnail, text=f'Title: {videoTitle} \nDuration: {duration}')
                self.thumbnail.pack(padx=10, pady=10)

                #only audio itag
                audio_itag = video_info['audio_itag']

                #show quality and itag with dropdown
                video = video_info['video']
                resolutions = []
                for idx, vid in enumerate(video):
                    reso = f"Video: {video[vid]['resolution']} __ tag: {video[vid]['itag']}"
                    resolutions.append(reso)
                resolutions.reverse()
                resolutions.append(f'Audio Only __ tag: {audio_itag}')
                self.resolution.configure(values=resolutions) #show itag and resolution options

                #show all component after provide url and clicked get_video
                self.get_video.configure(text='Get Video', state='normal')
                self.resolution.pack()
                self.dir_label.pack(padx=10, pady=10)
                self.dir_btn.pack()
                self.download_btn.pack(padx=5, pady=10)
            else:
                infoLabel.configure(text='Error: Invalid video url')
                infoLabel.pack()
                self.link.select_range(0, END)

        except Exception as e:
            self.get_video.configure(text='Get Video', state='normal')
            infoLabel.configure(text=f'Error: Something went wrong \nTry again!')
            infoLabel.pack()
            self.link.select_range(0, END)

    #grab the default download dir
    def get_default_dir(self):
        user_path = Path.home()
        return os.path.join(user_path, 'Downloads')

    #askdirectory from end user
    def get_download_dir(self):
        self.download_dir = filedialog.askdirectory()
        self.dir_label.configure(text=f'Download To:\n {self.download_dir}')

    #execute when download button clicked
    def startDownload(self):
        infoLabel.configure(text='', cursor='arrow')
        infoLabel.unbind("<Button-1>")
        infoLabel.pack()
        progressBar.pack_forget()
        cancel_btn.pack_forget()

        try:
            #get solution text from entry
            resolution = self.resolution.get()
            download_to = self.download_dir

            #if given dir doesn't exists then set default download dir
            if not os.path.exists(download_to):
                download_to = self.get_default_dir()
                infoLabel.configure(text=f'Download Folder! \nPath: {download_to}')
            
            #check if resolution selected or not
            if resolution == 'Select Type and Quality':
                infoLabel.configure(text='Please select video quality!')
            else:
                #show download tips to the end user
                self.helpText.configure(text=self.tips[0])

                #initializing if only audio
                is_only_audio = False
                if 'Audio' in resolution:
                    is_only_audio = True
                    #show aduio downloading  tips while downloading audio file
                    self.helpText.configure(text=self.tips[1])
                #get the itag
                itag = int(resolution.split(':')[-1])

                #set these btn to be disabled while downloading
                self.get_video.configure(state='disabled')
                self.dir_btn.configure(state='disabled')
                self.download_btn.configure(text='Downloading...', state='disabled')
                self.resolution.configure(state='disabled')

                #call download function with itag, download dir and is_only_audio
                self.youtubeObj.download(itag, download_to, audio_only=is_only_audio)

                #after download completed, set these button to clickable state
                self.get_video.configure(state='normal')
                self.dir_btn.configure(state='normal')
                self.download_btn.configure(text='Download', state='normal')
                self.resolution.configure(state='normal')

        except Exception as e:
            #if any exception occour, set these button to clickable satte
            infoLabel.configure(text=f'Error: Something went wrong \nTry again!')
            self.get_video.configure(text='Get Video', state='normal')
            self.resolution.configure(state='normal')
            self.download_btn.configure(text='Download', state='normal')

      
app = App()
app.mainloop()