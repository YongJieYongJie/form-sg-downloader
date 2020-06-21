# built-ins
import csv
import io
import json
import threading
import time
from collections import namedtuple, OrderedDict

# third-party
import tkinter as tk
import selenium
from tkinter import filedialog, messagebox, ttk

# current package
from formsgdownloader import formsg_driver
from formsgdownloader.pyinstaller_utils import get_path
from formsgdownloader.tk_utils import MenuAction, YjMenu, YjTreeview


HELP_MSG = '''
Version 1.0.0

Prerequisites:
  - Google Chrome: Please install Google Chrome on the system -
        https://www.google.com/chrome/
  - Chrome Driver: Please download the appropriate Chrome Driver for the Google
        Chrome - https://chromedriver.chromium.org/downloads

Usage:
  0. Provide the following configuration options:
    - Your government email for accessing FormSG
    - Path to the Chrome Driver
    - Path to the folder to save the downloaded data

  1. Add details for each form:
    - Enter the "Form Name", this is used for you to identify the entries, and
          can be anything.
    - Enter the "Form ID", this is the 24-characters long string at the end of
          the form's URL: https://form.gov.sg/#!/<Form ID is here>.
    - Enter the "Form Secret Key", this is the content of the secret key file
          when you created the form.

  2. Download the data:
    - Click on "Start Download"
    - Wait for the prompt that the one-time password has been sent to your
          email, click OK.
    - Enter the one-time password, and click "Continue".
    - (Optional) Click on the menu [View] > [Logs] to view the download progress
          and any errors.
'''.strip()


FAVICON_PATH = get_path(r'favicon.ico')


Widget = namedtuple('Widget', 'name type options geometry_manager geometry_options', defaults=[{}, 'pack', {}])
Action = namedtuple('Action', 'widget_name event callback')
Form = namedtuple('Form', 'name id secret_key')


class App:

    def __init__(self, master, menu=None):

        self.master = master
        self.menu = menu
        self.widgets = {}

        # Data
        self.chrome_driver_path = tk.StringVar()
        self.download_path = tk.StringVar()
        self.forms = OrderedDict()
        self.form_name = tk.StringVar()
        self.form_id = tk.StringVar()
        self.form_secret_key = tk.StringVar()
        self.email = tk.StringVar()
        self.one_time_password = tk.StringVar()

        # Initialize top-level components
        self.master.protocol('WM_DELETE_WINDOW', self.master.destroy)
        self.master.title('FormSG Data Downloader')
        self.master.iconbitmap(FAVICON_PATH)
        self.initialize_menu()

        # Initializing various internal components
        self.populate_widgets(master)
        self.initialize_widgets()
        self.bind_actions()
        self.initialize_log_window_and_logging()
        self.initialize_help_window()


#region Initialization Methods
    def initialize_log_window_and_logging(self):

        # Create logging window
        toplevel_log = tk.Toplevel(self.master)
        toplevel_log.withdraw()
        toplevel_log.title('Logs')
        toplevel_log.protocol('WM_DELETE_WINDOW', toplevel_log.withdraw)
        toplevel_log.iconbitmap(FAVICON_PATH)

        text_log = tk.Text(toplevel_log, state='normal')
        text_log.insert('end', 'Log Messages:\n')
        text_log['state'] = 'disabled'
        text_log.pack(fill=tk.BOTH)

        self.widgets['toplevel_log'] = toplevel_log
        self.widgets['text_log'] = text_log

        # Redirect STDOUT to logs
        self.logStream = io.StringIO()
        import sys
        sys.stdout = self.logStream

        # Poll for updates to logs
        def poll_log():
            while True:
                self.logStream.seek(0)
                msg = self.logStream.read()
                if msg:
                    text_log['state'] = 'normal'
                    text_log.insert('end', msg)
                    text_log['state'] = 'disabled'
                    self.logStream.seek(0)
                    self.logStream.truncate()
                time.sleep(1) # Polling interval

        threading.Thread(target=poll_log, daemon=True).start()

    def initialize_help_window(self):

        toplevel_help = tk.Toplevel(self.master)
        toplevel_help.withdraw()
        toplevel_help.title('Help')
        toplevel_help.protocol('WM_DELETE_WINDOW', toplevel_help.withdraw)
        toplevel_help.iconbitmap(FAVICON_PATH)

        text_help = tk.Text(toplevel_help, state='normal')
        text_help.insert('end', HELP_MSG)
        text_help['state'] = 'disabled'
        text_help.pack(fill=tk.BOTH)

        self.widgets['toplevel_help'] = toplevel_help
        self.widgets['text_help'] = text_help

    def initialize_menu(self):

        file_menu_items = [
            MenuAction('Load session...', self.load_session),
            MenuAction('Save session', self.save_session),
            MenuAction('Export forms', self.export_forms),
            MenuAction('Import forms', self.import_forms),
        ]

        for name, handler_or_submenu in reversed(file_menu_items):
            self.menu.add_to_file_menu(name, handler_or_submenu)

        additional_top_level_menu_items = [
            ('View', [
                MenuAction('Logs', self.show_logs),
            ]),
            MenuAction('Help', self.show_help),
        ]

        for name, handler_or_submenu in additional_top_level_menu_items:
            self.menu.add_command_or_submenu(name, handler_or_submenu)

    def populate_widgets(self, master):

        ROW_PADDING = 3
        COL_PADDING = 2

        WIDGETS = [
            Widget('frame_config', ttk.LabelFrame, {'text': 'Step 0: Configuration'}, 'grid', {'column': 0, 'row': 0, 'padx': 10, 'pady': 10}),

            Widget('label_email',
                ttk.Label, { 'parent': 'frame_config',
                             'text': 'User Email Address:'},
                'grid', {'column': 0, 'row': 0, 'pady': ROW_PADDING, 'padx': COL_PADDING}),
            Widget('entry_email',
                ttk.Entry, { 'parent': 'frame_config',
                             'textvariable': self.email},
                'grid', {'column': 1, 'row': 0, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'EW'}),
            Widget('button_set-chrome-driver-path',
                ttk.Button, { 'parent': 'frame_config',
                              'text': 'Click to set Chrome Driver path:'},
                'grid', {'column': 0, 'row': 1, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'EW'}),
            Widget('label_chrome-driver-path',
                ttk.Entry, { 'parent': 'frame_config',
                             'textvariable': self.chrome_driver_path,
                             'width': 64},
                'grid', {'column': 1, 'row': 1, 'pady': ROW_PADDING, 'padx': COL_PADDING}),
            Widget('button_set-download-path',
                ttk.Button, { 'parent': 'frame_config',
                              'text': 'Click to set download path:'},
                'grid', {'column': 0, 'row': 2, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'EW'}),
            Widget('label_download-path',
                ttk.Entry, {'parent': 'frame_config',
                            'textvariable': self.download_path,
                            'width': 64},
                'grid', {'column': 1, 'row': 2, 'pady': ROW_PADDING, 'padx': COL_PADDING}),

            Widget('frame_form', ttk.LabelFrame, {'text': 'Step 1: Load Forms'}, 'grid', {'column': 0, 'row': 1, 'padx': 10, 'pady': 10}),

            Widget('label_form-name',
                ttk.Label, {'parent': 'frame_form',
                            'text': 'Form Name:'},
                'grid', {'column': 0, 'row': 0, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'E'}),
            Widget('entry_form-name',
                ttk.Entry, {'parent': 'frame_form',
                            'width': 32,
                            'textvariable': self.form_name},
                'grid', {'column': 1, 'row': 0, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'W'}),
            Widget('label_form-id',
                ttk.Label, {'parent': 'frame_form',
                            'text': 'Form ID:'},
                'grid', {'column': 0, 'row': 1, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'E'}),
            Widget('entry_form-id',
                ttk.Entry, {'parent': 'frame_form',
                            'width': 32,
                            'textvariable': self.form_id},
                'grid', {'column': 1, 'row': 1, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'W'}),
            Widget('label_form-secret-key',
                ttk.Label, {'parent': 'frame_form',
                            'text': 'Form Secret Key:'},
                'grid', {'column': 0, 'row': 2, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'E'}),
            Widget('entry_form-secret-key',
                ttk.Entry, {'parent': 'frame_form',
                            'width': 32,
                            'textvariable': self.form_secret_key},
                'grid', {'column': 1, 'row': 2, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'W'}),
            Widget('button_add-form',
                ttk.Button, {'parent': 'frame_form',
                            'text': 'Add Form'},
                'grid', {'column': 0, 'row': 3, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'E'}),
            Widget('button_load-forms',
                ttk.Button, {'parent': 'frame_form',
                            'text': 'Load Forms'},
                'grid', {'column': 1, 'row': 3, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'sticky': 'W'}),
            Widget('tree_add-form',
                YjTreeview, {'parent': 'frame_form',
                             'columns': ('Name', 'ID', 'Secret Key'), 'show': 'tree headings'},
                'grid', {'column': 0, 'row': 4, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'columnspan': 2}),

            Widget('frame_download', ttk.LabelFrame, {'text': 'Step 2: Download Data'}, 'grid', {'column': 0, 'row': 2, 'padx': 10, 'pady': 10}),

            Widget('button_download-submissions',
                ttk.Button, {'parent': 'frame_download',
                            'text': 'Start Download'},
                'grid', {'column': 0, 'row': 0, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'columnspan': 2, 'sticky': 'EW'}),
            Widget('label_one-time-password',
                ttk.Label, {'parent': 'frame_download',
                            'text': 'One-Time Password:'},
                'grid', {'column': 0, 'row': 1, 'pady': ROW_PADDING, 'padx': COL_PADDING}),
            Widget('entry_one-time-password',
                ttk.Entry, {'parent': 'frame_download',
                            'textvariable': self.one_time_password, 'state': 'disabled'},
                'grid', {'column': 1, 'row': 1, 'pady': ROW_PADDING, 'padx': COL_PADDING}),
            Widget('button_continue',
                ttk.Button, {'parent': 'frame_download',
                            'text': 'Continue', 'state': 'disable'},
                'grid', {'column': 0, 'row': 2, 'pady': ROW_PADDING, 'padx': COL_PADDING, 'columnspan': 2}),
        ]

        for name, widget_type, options, geometry_manager, geometry_options in WIDGETS:
            parent = options.pop('parent', None)
            parent_widget = self.widgets.get(parent, master)
            w = widget_type(parent_widget, **options)
            getattr(w, geometry_manager)(**geometry_options)
            self.widgets[name] = w

        master.rowconfigure(0, weight=1)
        master.rowconfigure(1, weight=1)
        master.rowconfigure(2, weight=1)
        master.columnconfigure(0, weight=1)

    def initialize_widgets(self):

        pass

    def bind_actions(self):

        ACTIONS = [
            Action('button_set-chrome-driver-path', '<Button-1>',
                lambda _: self.set_chrome_driver_path()),
            Action('button_set-download-path', '<Button-1>',
                lambda _: self.set_download_path()),

            Action('button_add-form', '<Button-1>',
                lambda _: self.add_form()),
            Action('button_add-form', '<Button-1>',
                lambda _: self.add_form()),
            Action('button_load-forms', '<Button-1>',
                lambda _: self.import_forms()),

            Action('button_download-submissions', '<Button-1>',
                lambda _: self.download_all_forms()),
        ]

        for widget_name, event, callback in ACTIONS:
            self.widgets[widget_name].bind(event, callback, '+')
#endregion

#region GUI Event Handlers
    def show_logs(self):

        self.widgets['toplevel_log'].deiconify()

    def show_help(self):

        self.widgets['toplevel_help'].deiconify()

    def save_session(self):

        file_path = filedialog.asksaveasfilename(
            initialfile='untitled.formsg',
            filetypes=[('FormSG Project Files', '.formsg')],
            defaultextension='.formsg',
            confirmoverwrite=True)
        if file_path:
            print('[-->] Saving session to file:', file_path)
            data = {
                'forms': tuple(self.forms.keys()),
                'email': self.email.get(),
                'chrome_driver_path': self.chrome_driver_path.get(),
                'download_path': self.download_path.get(),
            }
            with open(file_path, 'wb') as out_file:
                out_file.write(json.dumps(data).encode('utf-8'))

    def load_session(self):

        file_path = filedialog.askopenfilename(
            initialfile='untitled.formsg',
            filetypes=[('FormSG Project Files', '.formsg')],
            defaultextension='.formsg',
        )
        if file_path:
            print('[<--] Loading session from file:', file_path)
            with open(file_path, 'rb') as in_file:
                raw_data = in_file.read()

            try:
                json_data = json.loads(raw_data.decode('utf-8'))
            except:
                pass
            else:
                for form_details in json_data['forms']:
                    self._add_form(Form(*form_details))
                self.email.set(json_data['email'])
                self.chrome_driver_path.set(json_data['chrome_driver_path'])
                self.download_path.set(json_data['download_path'])

    def export_forms(self):

        file_path = filedialog.asksaveasfilename(
            initialfile='formsg.csv',
            filetypes=[('FormSG Credentials File', '.csv')],
            defaultextension='.csv',
            confirmoverwrite=True)
        if file_path:
            print('[-->] Saving Form SG forms and credentials to:', file_path)
            with open(file_path, 'wt', encoding='utf-8') as out_file:
                for form in self.forms.keys():
                    out_file.write('{name},{id},{secret_key}\n'.format(**form._asdict()))

    def import_forms(self):

        cred_file_path = filedialog.askopenfilename(multiple=False,
            filetype=[('FormSG Credentials File', '*.csv')])

        if cred_file_path:
            with open(cred_file_path, 'rt', encoding='utf-8') as cred_file:
                content = cred_file.readlines()

            for details in content:
                form = Form(*details.strip().split(','))
                self._add_form(form)

    def set_chrome_driver_path(self):

        self.chrome_driver_path.set(filedialog.askopenfilename(multiple=False,
            filetype=[('ChromeDriver', 'chromedriver.exe')]))

    def set_download_path(self):

        self.download_path.set(filedialog.askdirectory())

    def add_form(self):

        form_name = self.form_name.get().strip()
        form_id = self.form_id.get().strip()
        form_secret_key = self.form_secret_key.get().strip()

        error_details = self.validate_input(form_name, form_id, form_secret_key)

        if error_details:
            messagebox.askokcancel('Error', message='Invalid input',
                detail=error_details, icon='error')
        else:
            form = Form(form_name, form_id, form_secret_key)
            self._add_form(form)

    def download_all_forms(self):

        threading.Thread(target=self._download_all_forms, daemon=True).start()

    def _download_all_forms(self):
        
        self.disable_all_widgets()

        # Initialize selenium_gui
        selenium_gui._set_forms_details(self.forms)
        selenium_gui._init(
            self.download_path.get(),
            self.chrome_driver_path.get(), force=True)

        # Log into form.gov.sg
        self.login_to_formsg()

        # Download data for each form
        for form in self.forms:
            try:
                selenium_gui.download_csv(form.name)
            except selenium.common.exceptions.WebDriverException as e:
                print(f'[!] Error downloading data from form: {form}.')
                print(e)
        print('[*] Download finished!')

        self.enable_all_widgets()
#endregion

#region GUI Methods
    def disable_all_widgets(self, excluding=None):

        if excluding is None:
            excluding = []

        for name, w in self.widgets.items():
            if name in excluding:
                continue

            try:
                w['state'] = 'disabled'
            except (TypeError, tk.TclError):
                pass

    def enable_all_widgets(self, excluding=None):

        if excluding is None:
            excluding = []

        for name, w in self.widgets.items():
            if name in excluding:
                continue

            try:
                w['state'] = 'normal'
            except tk.TclError:
                pass

    def clear_widgets(self, *widget_names):

        for widget in (self.widgets[name] for name in widget_names):
            if isinstance(widget, tk.Entry):
                widget.delete(0, 'end')
            else:
                raise NotImplementedError(
                    f'{__name__} does not support {type(widget)}')
#endregion

#region Helper Methods
    def login_to_formsg(self):

        selenium_gui.enter_email(self.email.get())

        continue_button_press = threading.Event()
        self.widgets['button_continue'].bind('<Button-1>',
            lambda _: continue_button_press.set())
        self.widgets['entry_one-time-password']['state'] = 'default'
        self.widgets['button_continue']['state'] = 'default'
        messagebox.askokcancel('One-Time Password', message='The one-time '
            'password (OTP) has been sent to your email. Enter the OTP in the '
            'main window and click "Continue" to download the data.',
            icon='info')
        continue_button_press.wait()

        self.widgets['entry_one-time-password']['state'] = 'disabled'
        self.widgets['button_continue']['state'] = 'disabled'
        otp = self.one_time_password.get()
        selenium_gui.enter_one_time_password(otp)

    def _add_form(self, form):

        if not form in self.forms:
            self.forms[form] = None
            self.widgets['tree_add-form'].add_item(*form)

    @staticmethod
    def validate_input(form_name, form_id, form_secret_key):

        errors = []

        if form_name == '':
            errors.append('Form Name cannot be empty.')

        if form_id == '':
            errors.append('Form ID cannot be empty.')
        elif len(form_id) != 24:
            errors.append('Form ID length incorrect.')

        if form_secret_key == '':
            errors.append('Form Secret Key cannot be empty.')
        elif len(form_secret_key) != 44:
            errors.append('Form Secret Key length incorrect.')

        return '\n'.join(errors)
#endregion


if __name__ == '__main__':

    root = tk.Tk()
    menu = YjMenu(root)
    root.config(menu=menu)
    app = App(root, menu)

    root.mainloop()
