import tkinter as tk
import customtkinter
from tkinter import ttk
import time
import pygetwindow as gw
from datetime import date, datetime, timedelta
import smtplib
import pandas as pd
import config
import threading

class AppUsageTracker(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("App Usage Tracker")
        self.geometry("600x400")
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("dark-blue")
        self.configure(bg_color="#282c34")  

        self.current_window = None
        self.start_time = None
        self.app_data = {}
        self.total_usage_today = 0
        self.today = date.today()
        self.today_adj = self.today.strftime("%B %d, %Y")
        self.yesterday = self.today - timedelta(days=1)
        self.yesterday = self.yesterday.strftime("%B %d, %Y")
        self.app_df = pd.read_csv("AppUsage.csv")
        self.yesterday_data = self.app_df[self.app_df['date'] == self.yesterday]

       
        self.tracking = False
        self.track_thread = None

        
        self.create_widgets()

    def create_widgets(self):
        self.start_button = customtkinter.CTkButton(self, text="Start Tracking", fg_color=("#6153B7", "#F047FE"), command=self.start_tracking)
        self.start_button.grid(row=0, column=0, padx=80, pady=20)

        self.stop_button = customtkinter.CTkButton(self, text="Stop Tracking", fg_color=("#F047FE", "#6153B7"), command=self.stop_tracking)
        self.stop_button.grid(row=0, column=1, padx=80, pady=20)

        self.current_app_label = customtkinter.CTkLabel(self, text="Current App: None")
        self.current_app_label.grid(row=1, column=0, columnspan=2, pady=10)

        self.current_app_label = customtkinter.CTkLabel(self, text="Current App: None", font=("Helvetica", 16, "bold"), text_color="white")
        self.current_app_label.grid(row=1, column=0, columnspan=2, pady=10)

        self.style = ttk.Style()
        self.style.theme_use("default")

        self.style.configure("Treeview", background="#282c34", foreground="white", fieldbackground="#282c34", font=("Helvetica", 12), borderwidth=0, rowheight=30)
        self.style.map('Treeview', background=[('selected', '#3B4252')])

        self.style.configure("Treeview.Heading", background="#4C566A", foreground="white", font=("Helvetica", 12, "bold"))

        self.tree = ttk.Treeview(self, columns=('App', 'Time'), show='headings')
        self.tree.heading('App', text='Application')
        self.tree.heading('Time', text='Time Spent (seconds)')

        self.tree.grid(row=2, column=0, columnspan=2, pady=10, sticky="nsew")

        self.usage_time_label = customtkinter.CTkLabel(self, text="Total Usage Today: 0 seconds", font=("Helvetica", 14), text_color="white")
        self.usage_time_label.grid(row=3, column=0, columnspan=2, pady=10)

        self.clock_label = customtkinter.CTkLabel(self, text="", font=("Helvetica", 12), text_color="white")
        self.clock_label.grid(row=4, column=0, columnspan=2, pady=10)
        self.update_clock()

    def update_clock(self):
        current_time = time.strftime("%H:%M:%S")
        self.clock_label.configure(text=current_time)
        self.after(1000, self.update_clock)

    def start_tracking(self):
        self.tracking = True
        self.start_button._state = "disabled"
        self.stop_button._state = "normal"
        self.track_thread = threading.Thread(target=self.track_app_time)
        self.track_thread.start()
        self.send_email()

    def stop_tracking(self):
        self.tracking = False
        self.start_button._state = "normal"
        self.stop_button._state = "disabled"
        if self.track_thread:
            self.track_thread.join()
        self.save_app_usage()

    def track_app_time(self):
        while self.tracking:
            new_window = gw.getActiveWindow()

            if new_window != self.current_window:
                if self.current_window is not None:
                    end_time = time.time()
                    elapsed_time = end_time - self.start_time
                    app_name = self.current_window.title

                    if app_name in self.app_data:
                        self.app_data[app_name] += elapsed_time
                    else:
                        self.app_data[app_name] = elapsed_time

                    self.update_display(app_name, self.app_data[app_name])
                    self.save_to_file(app_name, elapsed_time)

                self.current_window = new_window
                self.start_time = time.time()
                if self.current_window.title:
                    self.current_app_label.configure(text=f"Current App: {self.current_window.title}")
                else:
                    self.current_app_label.configure(text="Current App: Unknown")


            time.sleep(1)

    def update_display(self, app_name, total_time):
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][0] == app_name:
                self.tree.delete(item)
                break
        self.tree.insert('', 'end', values=(app_name, f"{total_time:.2f}"))

    def save_to_file(self, app_name, elapsed_time):
        with open("TrackRecords.txt", "a", encoding='utf-8') as file:
            current_datetime = time.strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{current_datetime} - Time spent on {app_name}: {elapsed_time:.2f} seconds\n")

    def send_email(self):
        print("Sent!")
        sender = f"Private Person <{config.send}>"
        receiver = f"A Test User <{config.rec}>"
        
        message = f"""\
Subject: Application Usage 
To: {receiver}
From: {sender}

Here is your application's usage data for {self.yesterday}:

"""

        for _, row in self.yesterday_data.iterrows():
            if row['isSent'] == 1:
                continue
            else:
                message += f"Application Name: {row['application_name']}\n"
                message += f"Usage: {row['application_usage']} seconds\n"

        notSent = self.yesterday_data[self.yesterday_data['isSent'] == 0]

        if notSent.shape[0] > 0:
            with smtplib.SMTP("live.smtp.mailtrap.io", 587) as server:
                server.starttls()
                server.login("api", config.api)
                server.sendmail(sender, receiver, message).encode('utf-8')

    def save_app_usage(self):
        for idx, row in self.yesterday_data.iterrows():
            self.app_df.loc[idx, 'isSent'] = 1

        app_usage_list = []

        for app, time_spent in self.app_data.items():
            self.app_df['application_usage'] = pd.to_numeric(self.app_df['application_usage'], errors='coerce').fillna(0)

            existing_row = self.app_df[(self.app_df['date'] == self.today_adj) & (self.app_df['application_name'] == app)]

            if not existing_row.empty:
                self.app_df.loc[existing_row.index, 'application_usage'] += time_spent
            else:
                new_row = {
                    'date': self.today_adj,
                    'application_name': app,
                    'application_usage': time_spent,
                    'isSent': 0,
                }
                app_usage_list.append(new_row)

        app_usage_df = pd.DataFrame(app_usage_list)
        combined_df = pd.concat([self.app_df, app_usage_df], ignore_index=True)
        combined_df.to_csv('AppUsage.csv', index=False)

if __name__ == "__main__":
    app = AppUsageTracker()
    app.mainloop()
    app.save_app_usage()