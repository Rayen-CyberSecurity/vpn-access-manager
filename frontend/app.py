"""VPN Access Manager — desktop client (tkinter)."""

import tkinter as tk
from tkinter import messagebox, ttk

from api_client import ApiClient, ApiError


class ConnectDialog(tk.Toplevel):
    """Screen 1: connect to the REST API."""

    def __init__(self, master):
        super().__init__(master)

        self.title("Connect")
        self.resizable(False, False)
        self.client = None

        frm = ttk.Frame(self, padding=16)
        frm.grid()

        ttk.Label(frm, text="API URL").grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.url = ttk.Entry(frm, width=34)
        self.url.insert(0, "http://localhost:8000")
        self.url.grid(
            row=0,
            column=1,
            pady=4,
        )

        ttk.Label(frm, text="API key").grid(
            row=1,
            column=0,
            sticky="w",
        )

        self.key = ttk.Entry(frm, width=34, show="*")
        self.key.insert(0, "dev-key")
        self.key.grid(
            row=1,
            column=1,
            pady=4,
        )

        ttk.Button(
            frm,
            text="Connect",
            command=self.attempt,
        ).grid(
            row=2,
            column=1,
            sticky="e",
            pady=(12, 0),
        )

        self.bind("<Return>", lambda _event: self.attempt())
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.update_idletasks()
        self.wait_visibility()
        self.grab_set()
    def attempt(self):
        client = ApiClient(
            self.url.get().strip(),
            self.key.get().strip(),
        )

        try:
            client.gateways()
        except ApiError as error:
            messagebox.showerror(
                "Connection failed",
                error.message,
                parent=self,
            )
            return

        self.client = client
        self.destroy()

    def cancel(self):
        self.client = None
        self.destroy()


class NewSessionDialog(tk.Toplevel):
    """Screen 3: open a new VPN session."""

    def __init__(self, master, client, gateways):
        super().__init__(master)

        self.title("New session")
        self.resizable(False, False)

        self.client = client
        self.gateways = gateways
        self.created = False

        frm = ttk.Frame(self, padding=16)
        frm.grid()

        ttk.Label(frm, text="User ID").grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.user_id = ttk.Entry(frm, width=34)
        self.user_id.insert(0, "7")
        self.user_id.grid(
            row=0,
            column=1,
            pady=4,
        )

        ttk.Label(frm, text="Gateway").grid(
            row=1,
            column=0,
            sticky="w",
        )

        self.gw_box = ttk.Combobox(
            frm,
            width=32,
            state="readonly",
            values=[
                (
                    f"{gateway['name']} "
                    f"({gateway['active_sessions']}/"
                    f"{gateway['max_sessions']})"
                )
                for gateway in gateways
            ],
        )

        if gateways:
            self.gw_box.current(0)

        self.gw_box.grid(
            row=1,
            column=1,
            pady=4,
        )

        ttk.Label(frm, text="Client IP").grid(
            row=2,
            column=0,
            sticky="w",
        )

        self.ip = ttk.Entry(frm, width=34)
        self.ip.insert(0, "192.168.50.10")
        self.ip.grid(
            row=2,
            column=1,
            pady=4,
        )

        self.msg = ttk.Label(
            frm,
            text="",
            foreground="#b00020",
            wraplength=320,
        )
        self.msg.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )

        ttk.Button(
            frm,
            text="Open session",
            command=self.submit,
        ).grid(
            row=4,
            column=1,
            sticky="e",
            pady=(12, 0),
        )

        self.update_idletasks()
        self.wait_visibility()

        self.grab_set()


    def submit(self):
        try:
            user_id = int(self.user_id.get().strip())
        except ValueError:
            self.msg.config(
                text="User ID must be an integer."
            )
            return

        if not self.gateways:
            self.msg.config(
                text="No gateways are available."
            )
            return

        gateway = self.gateways[self.gw_box.current()]

        try:
            self.client.open_session(
                user_id,
                gateway["id"],
                self.ip.get().strip(),
            )
        except ApiError as error:
            self.msg.config(text=error.message)
            return

        self.created = True
        self.destroy()


class SessionDetailDialog(tk.Toplevel):
    """Screen 4: show the details of one session."""

    def __init__(self, master, session):
        super().__init__(master)

        self.title(f"Session {session['id']} details")
        self.resizable(False, False)

        frm = ttk.Frame(self, padding=16)
        frm.grid()

        details = (
            ("Session ID", session["id"]),
            ("User", session["username"]),
            ("Department", session["department"]),
            ("Gateway", session["gateway_name"]),
            ("Status", session["status"]),
            ("Client IP", session["client_ip"]),
            ("Connected at", session["connected_at"]),
            ("Disconnected at", session["disconnected_at"] or "-"),
            ("Bytes transferred", f"{session['bytes_transferred']:,}"),
        )

        for row, (label, value) in enumerate(details):
            ttk.Label(
                frm,
                text=label,
                font=("TkDefaultFont", 9, "bold"),
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                frm,
                text=str(value),
            ).grid(
                row=row,
                column=1,
                sticky="w",
                pady=3,
            )

        ttk.Button(
            frm,
            text="Close",
            command=self.destroy,
        ).grid(
            row=len(details),
            column=1,
            sticky="e",
            pady=(12, 0),
        )


        self.update_idletasks()
        self.wait_visibility()
        self.grab_set()


class MainWindow(ttk.Frame):
    """Screen 2: gateway overview and session list."""

    def __init__(self, master, client):
        super().__init__(master, padding=12)

        self.client = client
        self.gateways = []

        self.grid(sticky="nsew")

        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        ttk.Label(
            self,
            text="Gateways",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.gw_tree = ttk.Treeview(
            self,
            columns=("region", "load", "ip"),
            height=4,
        )

        self.gw_tree.heading("#0", text="Name")
        self.gw_tree.column("#0", width=100)

        for column, heading, width in (
            ("region", "Region", 120),
            ("load", "Active / Max", 130),
            ("ip", "Public IP", 260),
        ):
            self.gw_tree.heading(column, text=heading)
            self.gw_tree.column(
                column,
                width=width,
                anchor="w",
            )

        self.gw_tree.tag_configure(
            "full",
            background="#ffe0e0",
        )

        self.gw_tree.grid(
            row=1,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(4, 12),
        )

        ttk.Label(
            self,
            text="Sessions",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(
            row=2,
            column=0,
            sticky="w",
        )

        self.s_tree = ttk.Treeview(
            self,
            columns=(
                "user",
                "department",
                "gw",
                "status",
                "ip",
                "since",
                "bytes",
            ),
            show="headings",
            height=12,
        )

        for column, heading, width in (
            ("user", "User", 100),
            ("department", "Department", 110),
            ("gw", "Gateway", 100),
            ("status", "Status", 80),
            ("ip", "Client IP", 120),
            ("since", "Connected at", 170),
            ("bytes", "Bytes", 100),
        ):
            self.s_tree.heading(column, text=heading)
            self.s_tree.column(
                column,
                width=width,
                anchor="w",
            )

        self.s_tree.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="nsew",
            pady=4,
        )

        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)

        ttk.Button(
            self,
            text="New session",
            command=self.new_session,
        ).grid(
            row=4,
            column=0,
            sticky="w",
            pady=8,
        )

        ttk.Button(
            self,
            text="View details",
            command=self.view_details,
        ).grid(
            row=4,
            column=1,
            sticky="w",
            pady=8,
        )

        ttk.Button(
            self,
            text="Disconnect",
            command=self.disconnect,
        ).grid(
            row=4,
            column=2,
            sticky="w",
            pady=8,
        )

        ttk.Button(
            self,
            text="Refresh",
            command=self.refresh,
        ).grid(
            row=4,
            column=3,
            sticky="e",
            pady=8,
        )

        self.status = ttk.Label(
            self,
            text="",
        )
        self.status.grid(
            row=5,
            column=0,
            columnspan=4,
            sticky="w",
        )

        self.refresh()

    def refresh(self):
        try:
            self.gateways = self.client.gateways()
            sessions = self.client.sessions()
        except ApiError as error:
            messagebox.showerror(
                "Error",
                error.message,
                parent=self,
            )
            return

        self.gw_tree.delete(
            *self.gw_tree.get_children()
        )

        for gateway in self.gateways:
            full = (
                gateway["active_sessions"]
                >= gateway["max_sessions"]
            )

            self.gw_tree.insert(
                "",
                "end",
                iid=str(gateway["id"]),
                text=gateway["name"],
                values=(
                    gateway["region"],
                    (
                        f"{gateway['active_sessions']} / "
                        f"{gateway['max_sessions']}"
                        + ("   FULL" if full else "")
                    ),
                    gateway["public_ip"],
                ),
                tags=("full",) if full else (),
            )

        self.s_tree.delete(
            *self.s_tree.get_children()
        )

        for session in sessions:
            self.s_tree.insert(
                "",
                "end",
                iid=str(session["id"]),
                values=(
                    session["username"],
                    session["department"],
                    session["gateway_name"],
                    session["status"],
                    session["client_ip"],
                    session["connected_at"][:19].replace(
                        "T",
                        " ",
                    ),
                    f"{session['bytes_transferred']:,}",
                ),
            )

        self.status.config(
            text=f"{len(sessions)} sessions loaded."
        )

    def new_session(self):
        dialog = NewSessionDialog(
            self.winfo_toplevel(),
            self.client,
            self.gateways,
        )

        self.wait_window(dialog)

        if dialog.created:
            self.refresh()

    def view_details(self):
        selected = self.s_tree.selection()

        if not selected:
            messagebox.showinfo(
                "Session details",
                "Select a session first.",
                parent=self,
            )
            return

        session_id = int(selected[0])

        try:
            session = self.client.get_session(session_id)
        except ApiError as error:
            messagebox.showerror(
                "Error",
                error.message,
                parent=self,
            )
            return

        dialog = SessionDetailDialog(
            self.winfo_toplevel(),
            session,
        )

        self.wait_window(dialog)

    def disconnect(self):
        selected = self.s_tree.selection()

        if not selected:
            messagebox.showinfo(
                "Disconnect",
                "Select a session first.",
                parent=self,
            )
            return

        session_id = int(selected[0])
        values = self.s_tree.item(selected[0])["values"]

        if values[3] != "active":
            messagebox.showinfo(
                "Disconnect",
                "That session is already closed.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Disconnect",
            (
                f"Close session {session_id} for "
                f"{values[0]} on {values[2]}?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            self.client.close_session(
                session_id,
                bytes_transferred=5242880,
            )
        except ApiError as error:
            messagebox.showerror(
                "Error",
                error.message,
                parent=self,
            )
            return

        self.refresh()


def main():
    root = tk.Tk()

    root.title("VPN Access Manager")
    root.geometry("1000x620")
    root.withdraw()

    dialog = ConnectDialog(root)
    root.wait_window(dialog)

    if dialog.client is None:
        root.destroy()
        return

    root.deiconify()

    MainWindow(
        root,
        dialog.client,
    )

    root.mainloop()


if __name__ == "__main__":
    main()
