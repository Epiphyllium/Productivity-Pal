from datetime import datetime
import subprocess
import re


class AppleScript():
    def __init__(self):
        print("AppleScript initialized")

    # 输出脚本执行的返回
    def run_applescript(self,applescript):
        process = subprocess.Popen(['osascript', '-e', applescript], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if process.returncode == 0:
            print("Script executed successfully")
            return output.decode().strip()
        else:
            print(f"Script executed failed: {error.decode()}")

    def create_reminder_script(self,title, date, time):
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        # formatted_date = date_obj.strftime("%A, %B %d, %Y")
        applescript = f'''
        on createReminder(reminderTitle, reminderDate, reminderTime)
            tell application "Reminders"
                set fullDateTime to reminderDate & " " & reminderTime
                set newReminder to make new reminder with properties {{name:reminderTitle, remind me date:date fullDateTime}}
            end tell
        end createReminder

        createReminder("{title}", "{date}", "{time}")
        '''
        return applescript


    def create_event_script(self,event_title, event_date, event_start_time, event_end_time):
        date_obj = datetime.strptime(event_date, "%Y-%m-%d")
        # 获取年、月、日
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        day = date_obj.strftime("%d")

        applescript = f'''
        on createEvent(eventTitle, eventYear, eventMonth, eventDay, eventStartTime, eventEndTime)
            tell application "Calendar"
                tell calendar "Home"
                -- Set start date
                set my_start_date to current date
                set year of my_start_date to eventYear as integer
                set month of my_start_date to eventMonth as integer
                set day of my_start_date to eventDay as integer
                
                -- Parse start time
                set start_hours to (text 1 thru 2 of eventStartTime) as integer
                set start_minutes to (text 4 thru 5 of eventStartTime) as integer
                if eventStartTime contains "PM" and start_hours ≠ 12 then
                    set start_hours to start_hours + 12
                else if eventStartTime contains "AM" and start_hours = 12 then
                    set start_hours to 0
                end if
                set time of my_start_date to (start_hours * 3600 + start_minutes * 60)
                
                -- Set end date
                set my_end_date to current date
                set year of my_end_date to eventYear as integer
                set month of my_end_date to eventMonth as integer
                set day of my_end_date to eventDay as integer
                
                -- Parse end time
                set end_hours to (text 1 thru 2 of eventEndTime) as integer
                set end_minutes to (text 4 thru 5 of eventEndTime) as integer
                if eventEndTime contains "PM" and end_hours ≠ 12 then
                    set end_hours to end_hours + 12
                else if eventEndTime contains "AM" and end_hours = 12 then
                    set end_hours to 0
                end if
                set time of my_end_date to (end_hours * 3600 + end_minutes * 60)
                
                -- Check if start time is earlier than end time
                if my_start_date ≥ my_end_date then
                    error "Start time must be earlier than end time."
                end if
                
                -- Create event
                make new event with properties {{summary:eventTitle, start date:my_start_date, end date:my_end_date}}
                end tell
            end tell
        end createEvent

        createEvent("{event_title}", "{year}", "{month}", "{day}", "{event_start_time}", "{event_end_time}")
        '''
        return applescript

    # combine the two scripts functions
    def add_event(self,event_title, event_date, event_start_time, event_end_time):
        reminder_script = self.create_reminder_script(event_title, event_date, event_start_time)
        event_script = self.create_event_script(event_title, event_date, event_start_time, event_end_time)
        self.run_applescript(reminder_script)
        self.run_applescript(event_script)

    # Get the completed reminders within a specified time range
    def get_completed_reminders(self,start_time, end_time):
        start_time = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y-%m-%d 00:00:00")
        end_time = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y-%m-%d 23:59:59")
        
        applescript = f'''
        on get_completed_reminders_within()
            set theReminders to {{}}
            set startDate to date "{start_time}"
            set endDate to date "{end_time}"
            tell application "Reminders"
                repeat with r in (reminders whose completed is true)
                    set completionDate to completion date of r
                    if completionDate ≥ startDate and completionDate ≤ endDate then
                        set end of theReminders to name of r
                    end if
                end repeat
            end tell
            return theReminders
        end get_completed_reminders_within

        get_completed_reminders_within()
        '''
        return applescript

    # Get the uncompleted reminders within a specified time range
    def get_uncompleted_reminders(self):
        applescript = '''
        on get_overdue_incomplete_reminders()
            set theReminders to {}
            set currentDate to current date
            set lastWeekDate to currentDate - (7 * days)
            tell application "Reminders"
                repeat with r in (reminders whose completed is false)
                    set dueDate to due date of r
                    if dueDate is not missing value and dueDate < currentDate and dueDate>=lastWeekDate then
                        set end of theReminders to name of r
                    end if
                end repeat
            end tell
            return theReminders
        end get_overdue_incomplete_reminders

        get_overdue_incomplete_reminders()
        '''
        return applescript

    def get_busy_times(self,endTime):
        end_time = datetime.strptime(endTime, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        
        applescript = f'''
        on get_busy_times_before()
            set busyTimes to {{}}
            set startDate to current date
            set endDate to date "{end_time}"
            tell application "Calendar"
                repeat with c in calendars
                    set eventsInRange to (events of c whose start date ≥ startDate and start date ≤ endDate)
                    repeat with e in eventsInRange
                        set eventTitle to summary of e
                        set eventStartDate to start date of e
                        set eventEndDate to end date of e
                        set end of busyTimes to {{eventTitle, eventStartDate as string, eventEndDate as string}}
                    end repeat
                end repeat
            end tell
            return busyTimes
        end get_busy_times_before

        get_busy_times_before()
        '''
        return applescript

    # Get the calendar events between now and the specified time
    def get_calendar_events(self,deadline):
        get_busy_times_script = self.get_busy_times(deadline)
        output = self.run_applescript(get_busy_times_script)
        if output == None:
            return []
        mid=output.split(", ")
        events=[]
        i=0
        while i<len(mid)-2:
            stDate,stDateTime = self.parse_custom_date_time(mid[i+1])
            edDate,edDateTime = self.parse_custom_date_time(mid[i+2])
            # if the event is an all-day event, skip it
            if stDate==edDate and int(edDateTime)-int(stDateTime)==2359:
                i+=3
                continue
            duration=[stDate,stDateTime,edDate,edDateTime]
            events.append({mid[i]:duration})
            i+=3
        return events

    def parse_custom_date_time(self,date_time_str):
        # date_time_str = "2024年11月25日 下午2:00:00"
        match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日.*(\d{2}:\d{2}:\d{2})", date_time_str)
        if not match:
            raise ValueError("wrong date time format")
        
        year, month, day, time = match.groups()
        date_formatted = f"{year}{int(month):02d}{int(day):02d}"
        datetime_str = f"{date_formatted}{time.replace(':', '')[:4]}"
        
        return date_formatted, datetime_str

if __name__ == "__main__":
    eventName = "会议"
    eventDate = "2024-11-25"
    eventStartTime = "10:00"
    eventEndTime = "14:00"
    asp = AppleScript()
    reminder_script = asp.create_reminder_script(eventName, eventDate, eventStartTime)
    event_script = asp.create_event_script(eventName, eventDate, eventStartTime, eventEndTime)
    asp.run_applescript(reminder_script)
    asp.run_applescript(event_script)
    # get_reminder_script=get_completed_reminders("2020-11-01", "2024-11-30")
    # get_uncompleted_reminders_script = get_uncompleted_reminders()
    # print(run_applescript(get_reminder_script).split(", "))
    # print(run_applescript(get_uncompleted_reminders_script).split(", "))
    # print(get_calendar_events("2024-11-30 23:59:59"))