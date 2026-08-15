"""VPN Access Manager — desktop client (tkinter)."""

import sys
import tkinter as tk
from tkinter import messagebox, ttk

from api_client import ApiClient, ApiError


class ConnectDialog(tk.Toplevel):
    """Screen 1: where to connect and with which key."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Connect")
        self.resizable(False, False)
        self.client = None

        frm = ttk.Frame(self, padding=16)
        frm.grid()

        ttk.Label(frm, text="API URL").grid(row=0, column=0, sticky="w")
        self.url = ttk.Entry(frm, width=34)
        self.url.insert(0, "http://localhost:8000")
        self.url.grid(row=0, column=1, pady=4)

        ttk.Label(frm, text="API key").grid(row=1, column=0, sticky="w")
        self.key = ttk.Entry(frm, width=34, show="*")
        self.key.insert(0, "dev-key")
        self.key.grid(row=1, column=1, pady=4)

        ttk.Button(frm, text="Connect", command=self.attempt).grid(
            row=2, column=1, sticky="e", pady=(12, 0)
        )
        self.bind("<Return>", lambda _e: self.attempt())

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.grab_set()

    def attempt(self):
        client = ApiClient(self.url.get().strip(), self.key.get().strip())
        try:
            client.health()
        except ApiError as e:
            # a clean message, never a stack trace
            messagebox.showerror("Connection failed", e.message, parent=self)
            return
        self.client = client
        self.destroy()

    def cancel(self):
        self.client = None
        self.destroy()


class NewSessionDialog(tk.Toplevel):
    """Screen 3: open a session. Does NOT pre-check capacity."""

    def __init__(self, master, client, users, gateways):
        super().__init__(master)
        self.title("New session")
        self.resizable(False, False)
        self.client = client
        self.created = False

        self.users = users
        self.gateways = gateways

        frm = ttk.Frame(self, padding=16)
        frm.grid()

        ttk.Label(frm, text="User").grid(row=0, column=0, sticky="w")
        self.user_box = ttk.Combobox(
            frm, width=32, state="readonly",
            values=[f"{u['username']} - {u['full_name']}" for u in users],
        )
        self.user_box.current(0)
        self.user_box.grid(row=0, column=1, pady=4)

        ttk.Label(frm, text="Gateway").grid(row=1, column=0, sticky="w")
        self.gw_box = ttk.Combobox(
            frm, width=32, state="readonly",
            values=[
                f"{g['name']}  ({g['active_sessions']}/{g['max_sessions']})"
                for g in gateways
            ],
        )
        self.gw_box.current(0)
        self.gw_box.grid(row=1, column=1, pady=4)

        ttk.Label(frm, text="Client IP").grid(row=2, column=0, sticky="w")
        self.ip = ttk.Entry(frm, width=34)
        self.ip.insert(0, "192.168.50.10")
        self.ip.grid(row=2, column=1, pady=4)

        self.msg = ttk.Label(frm, text="", foreground="#b00020", wraplength=320)
        self.msg.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Button(frm, text="Open session", command=self.submit).grid(
            row=4, column=1, sticky="e", pady=(12, 0)
        )
        self.grab_set()

    def submit(self):
        user = self.users[self.user_box.current()]
        gw = self.gateways[self.gw_box.current()]
        try:
            self.client.open_session(user["id"], gw["id"], self.ip.get().strip())
        except ApiError as e:
            # the server's message, unchanged
            self.msg.config(text=e.message)
            return
        self.created = True
        self.destroy()


class MainWindow(ttk.Frame):
    """Screen 2: gateway overview and session list."""

    def __init__(self, master, client):
        super().__init__(master, padding=12)
        self.client = client
        self.gateways = []
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        ttk.Label(self, text="Gateways", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.gw_tree = ttk.Treeview(
            self, columns=("region", "load", "host"), height=4
        )
        self.gw_tree.heading("#0", text="Name")
        self.gw_tree.column("#0", width=100)
        for col, head, w in (
            ("region", "Region", 120),
            ("load", "Active / Max", 130),
            ("host", "Hostname", 260),
        ):
            self.gw_tree.heading(col, text=head)
            self.gw_tree.column(col, width=w, anchor="w")
        self.gw_tree.tag_configure("full", background="#ffe0e0")
        self.gw_tree.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 12))

        ttk.Label(self, text="Sessions", font=("TkDefaultFont", 11, "bold")).grid(
            row=2, column=0, sticky="w"
        )
        self.s_tree = ttk.Treeview(
            self,
            columns=("user", "gw", "status", "ip", "since", "bytes"),
            show="headings",
            height=12,
        )
        for col, head, w in (
            ("user", "User", 110),
            ("gw", "Gateway", 100),
            ("status", "Status", 80),
            ("ip", "Client IP", 130),
            ("since", "Connected at", 170),
            ("bytes", "Bytes", 110),
        ):
            self.s_tree.heading(col, text=head)
            self.s_tree.column(col, width=w, anchor="w")
        self.s_tree.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=4)
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)

        ttk.Button(self, text="New session", command=self.new_session).grid(
            row=4, column=0, sticky="w", pady=8
        )
        ttk.Button(self, text="Disconnect", command=self.disconnect).grid(
            row=4, column=1, sticky="w", pady=8
        )
        ttk.Button(self, text="Refresh", command=self.refresh).grid(
            row=4, column=2, sticky="e", pady=8
        )

        self.status = ttk.Label(self, text="")
        self.status.grid(row=5, column=0, columnspan=3, sticky="w")

        self.refresh()

    def refresh(self):
        try:
            self.gateways = self.client.gateways()
            sessions = self.client.sessions()
        except ApiError as e:
            messagebox.showerror("Error", e.message, parent=self)
            return

        self.gw_tree.delete(*self.gw_tree.get_children())
        for g in self.gateways:
            full = g["active_sessions"] >= g["max_sessions"]
            self.gw_tree.insert(
                "", "end", iid=str(g["id"]), text=g["name"],
                values=(
                    g["region"],
                    f"{g['active_sessions']} / {g['max_sessions']}"
                    + ("   FULL" if full else ""),
                    g["hostname"],
                ),
                tags=("full",) if full else (),
            )

        self.s_tree.delete(*self.s_tree.get_children())
        for s in sessions:
            self.s_tree.insert(
                "", "end", iid=str(s["id"]),
                values=(
                    s["username"], s["gateway_name"], s["status"], s["client_ip"],
                    s["connected_at"][:19].replace("T", " "),
                    f"{s['bytes_transferred']:,}",
                ),
            )
        self.status.config(text=f"{len(sessions)} sessions loaded.")

    def new_session(self):
        try:
            users = self.client.users()
        except ApiError as e:
            messagebox.showerror("Error", e.message, parent=self)
            return
        dlg = NewSessionDialog(self.winfo_toplevel(), self.client, users,
                               self.gateways)
        self.wait_window(dlg)
        if dlg.created:
            self.refresh()

    def disconnect(self):
        sel = self.s_tree.selection()
        if not sel:
            messagebox.showinfo("Disconnect", "Select a session first.",
                                parent=self)
            return
        sid = int(sel[0])
        values = self.s_tree.item(sel[0])["values"]
        if values[2] != "active":
            messagebox.showinfo("Disconnect", "That session is already closed.",
                                parent=self)
            return
        if not messagebox.askyesno(
            "Disconnect",
            f"Close session {sid} for {values[0]} on {values[1]}?",
            parent=self,
        ):
            return
        try:
            self.client.close_session(sid, bytes_transferred=5242880)
        except ApiError as e:
            messagebox.showerror("Error", e.message, parent=self)
            return
        self.refresh()


def main():
    root = tk.Tk()
    root.title("VPN Access Manager")
    root.geometry("900x620")
    root.withdraw()

    dlg = ConnectDialog(root)
    root.wait_window(dlg)
    if dlg.client is None:
        root.destroy()
        sys.exit(0)

    root.deiconify()
    MainWindow(root, dlg.client)
    root.mainloop()


if __name__ == "__main__":
    main()
