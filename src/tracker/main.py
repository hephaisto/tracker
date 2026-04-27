import datetime
from pathlib import Path
from dataclasses import dataclass
import logging
import io
import random
import string

from nicegui import ui, app
from sqlalchemy import Integer, String, Boolean, DateTime, Interval, create_engine, select, func, MetaData, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from sqlalchemy.ext.orderinglist import ordering_list
from starlette.responses import PlainTextResponse

class Base(DeclarativeBase):
    pass

class TrackerGroup(Base):
    __tablename__ = "tracker_group"

    id: Mapped[int] = mapped_column(primary_key=True)
    trackers: Mapped[list["Tracker"]] = relationship(back_populates="group")
    access_codes: Mapped[list["AccessCode"]] = relationship(back_populates="group")

class Tracker(Base):
    __tablename__ = "tracker"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("tracker_group.id"))
    group: Mapped["TrackerGroup"] = relationship(back_populates="trackers")
    name: Mapped[str] = mapped_column(String(100))
    allowed_states: Mapped[list["State"]] = relationship(back_populates="tracker", order_by="State.order_number", collection_class=ordering_list("order_number"))

class State(Base):
    __tablename__ = "state"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    tracker_id: Mapped[int] = mapped_column(ForeignKey("tracker.id"))
    tracker: Mapped["Tracker"] = relationship(back_populates="allowed_states")
    events: Mapped[list["Event"]] = relationship(back_populates="state")
    order_number: Mapped[int] = mapped_column(Integer)
    color: Mapped[str] = mapped_column(String(7), default="#E0E0E0")
    visible: Mapped[bool] = mapped_column(Boolean, default=True)

class Event(Base):
    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True)

    state_id: Mapped[int] = mapped_column(ForeignKey("state.id"))
    state: Mapped["State"] = relationship(back_populates="events")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)

access_code_length = 20

class AccessCode(Base):
    __tablename__ = "access_code"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("tracker_group.id"))
    group: Mapped["TrackerGroup"] = relationship(back_populates="access_codes")
    
    code: Mapped[str] = mapped_column(String(access_code_length))
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
    track: Mapped[bool] = mapped_column(Boolean, default=False)
    view: Mapped[bool] = mapped_column(Boolean, default=False)
    access_range: Mapped[datetime.timedelta] = mapped_column(Interval, default=datetime.timedelta(seconds=0))

def generate_new_code():
    return "".join(random.SystemRandom().choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=access_code_length))

master_access_code = generate_new_code()
print(f"master access code is: {master_access_code}")

engine = create_engine("sqlite:////root/data.sqlite", echo=True)
Base.metadata.create_all(engine)

def make_test_data():
    with Session(engine) as session:
        group = session.scalar(select(TrackerGroup).where(TrackerGroup.id.is_(0)))
        if not group:
            group = TrackerGroup(
                    trackers=[
                        Tracker(
                            name="main activity",
                            allowed_states=[
                                State(name="sleep",
                                      events=[Event(timestamp=datetime.datetime.now()-datetime.timedelta(hours=1))],
                                      ),
                                State(name="transit",
                                      events=[Event(timestamp=datetime.datetime.now())],
                                      ),
                                State(name="work"),
                                State(name="eat"),
                                State(name="shower"),
                                ]
                            ),
                        Tracker(
                            name="something",
                            allowed_states=[
                                State(name="active"),
                                State(name="off"),
                                ]
                            )
                        ],
                    access_codes=[
                        AccessCode(code="readtoken", view=True, access_range=datetime.timedelta(days=10000)),
                        AccessCode(code="admintoken", admin=True, view=True, access_range=datetime.timedelta(days=10000)),
                        AccessCode(code="tracktoken", track=True, view=True, access_range=datetime.timedelta(hours=2)),
                        ]
                    )
            session.add_all([group])
            session.commit()

make_test_data()


@dataclass
class Access:
    admin: bool = False
    track: bool = False
    view: bool = False
    access_range: datetime.timedelta = datetime.timedelta(seconds=0)

def get_access(tracker_group: int, access_id: str) -> Access|None:
    if access_id == master_access_code:
        return Access(admin=True)
    with Session(engine) as session:
        access: AccessCode = session.scalar(select(AccessCode).where(AccessCode.code.is_(access_id)).where(AccessCode.group_id.is_(tracker_group)))
        if not access:
            return None
        return Access(admin=access.admin, track=access.track, view=access.view, access_range=access.access_range)

def deny():
    ui.label("not found or no access")


@ui.page("/master/{access_code}")
def master_access(access_code: str):
    if access_code != master_access_code:
        deny()
    else:
        with Session(engine) as session:
            groups = session.scalars(select(TrackerGroup))
            with ui.grid(columns="auto auto"):
                for group in groups:
                    ui.label(str(group.id))
                    copyable_page_link("admin", tracker_group=group.id, access_id=access_code)
            ui.button("new group", icon="add", on_click=create_group)

def create_group():
    with Session(engine) as session:
        group = TrackerGroup(
                access_codes=[
                    AccessCode(admin=True, code=generate_new_code()),
                    ]
                )
        session.add(group)
        session.commit()


@ui.page("/{access_id}/{tracker_group}")
def main(tracker_group: int, access_id: str):
    access: Access|None = get_access(tracker_group, access_id)
    if access is None:
        deny()
    else:
        if access.admin:
            copyable_page_link("admin", tracker_group=tracker_group, access_id=access_id)
        if access.track or access.view:
            copyable_page_link("track", tracker_group=tracker_group, access_id=access_id)


@ui.page("/{access_id}/{tracker_group}/track")
def track(tracker_group: int, access_id: str):
    access: Access|None = get_access(tracker_group, access_id)
    if access is None:
        deny()
    else:
        with Session(engine) as session:
            group = session.scalar(select(TrackerGroup).where(TrackerGroup.id.is_(tracker_group)))
            assert group is not None # otherwise, there would be no access
            if access.track:
                with ui.grid(columns="auto auto"):
                    for tracker in group.trackers:
                        ui.label(tracker.name)
                        with ui.row():
                            for state in tracker.allowed_states:
                                if state.visible:
                                    ui.button(state.name, color=state.color, on_click=lambda state=state.id: log_event(state))
                            ui.button("", icon="settings", color="grey", on_click=lambda t=tracker.id: ui.navigate.to(app.url_path_for("edit_tracker", tracker_id=t, access_id=access_id)))
                    new_tracker_name = ui.input(label="new")
                    ui.button("new tracker", icon="add", color="grey", on_click=lambda tg=tracker_group, tn=new_tracker_name: new_tracker(tg, tn.value))
                with ui.row():
                    ui.label("manual input")
                    state_select = ui.select({state.id: f"{tracker.name} / {state.name}" for tracker in group.trackers for state in tracker.allowed_states})
                    date_select = ui.date_input(value=datetime.date.today().isoformat())
                    time_select = ui.time_input()
                    ui.button("log", on_click=lambda s=state_select, d=date_select, t=time_select: log_event_manually(s.value, d.value, t.value))
            else:
                ui.label("no tracking access")

            ui.separator()

            if access.view:
                events = select(Event).join(Event.state).join(State.tracker).join(Tracker.group).where(TrackerGroup.id.is_(tracker_group)).where(Event.timestamp > datetime.datetime.now()-access.access_range).order_by(Event.timestamp.desc())
                with ui.grid(columns="auto auto auto"):
                    for event in session.scalars(events):
                        ui.label(event.timestamp.isoformat(sep=" ", timespec="seconds"))
                        ui.label(event.state.tracker.name)
                        ui.label(event.state.name)
            else:
                ui.label("no view access")

def new_tracker(tracker_group: int, tracker_name: str):
    if not tracker_name:
        ui.notify("no tracker name given")
        return
    with Session(engine) as session:
        tracker = session.scalar(select(Tracker).where(Tracker.group_id.is_(tracker_group)).where(Tracker.name.is_(tracker_name)))
        if tracker is not None:
            ui.notify("tracker with this name already exists")
            return
        tracker = Tracker(name=tracker_name, group_id=tracker_group)
        session.add(tracker)
        session.commit()


def icon_if_enabled(icon_name: str, enabled: bool):
    if enabled:
        ui.icon(icon_name).classes("text-xl")
    else:
        ui.label("")

def text_with_help(text: str, help_text: str):
    with ui.row().classes('items-center gap-1'):
        ui.label(text)
        ui.icon("help").classes("text-xl")
        ui.tooltip(help_text)

@ui.page("/{access_id}/{tracker_group}/admin")
def admin(tracker_group: int, access_id: str):
    access: Access = get_access(tracker_group, access_id)
    if access is None or not access.admin:
        deny()
    else:
        with Session(engine) as session:
            group = session.scalar(select(TrackerGroup).where(TrackerGroup.id.is_(tracker_group)))
            assert group is not None # otherwise, there would be no access
            with ui.grid(columns="auto auto auto auto auto auto auto auto"):
                ui.label("code")
                text_with_help("admin", "allows to manage access codes")
                text_with_help("track", "allows to enter new events")
                text_with_help("view", "allows viewing of tracked events")
                text_with_help("days", "sets the time range how long events are visible")
                ui.label("minutes")
                ui.label("actions")
                ui.label("link")

                for access_code in group.access_codes:
                    ui.label(access_code.code)
                    icon_if_enabled("settings", access_code.admin)
                    icon_if_enabled("edit", access_code.track)
                    icon_if_enabled("menu_book", access_code.view)
                    ui.label(str(access_code.access_range.days))
                    ui.label(str(access_code.access_range.seconds//60))
                    ui.button("delete", icon="delete", on_click=lambda a=access_code.id: delete_access_code(a))
                    copyable_page_link("main", tracker_group=tracker_group, access_id=access_code.code)


                ui.label("CREATE NEW")
                check_admin = ui.checkbox("")
                check_track = ui.checkbox("")
                check_view = ui.checkbox("")
                days = ui.number(value=1, precision=0, min=0)
                minutes = ui.number(value=1, precision=0, min=0)
                ui.button("create", icon="add", on_click=lambda g=tracker_group, a=check_admin, t=check_track, v=check_view, d=days, m=minutes: create_access_token(g, a.value, t.value, v.value, d.value, m.value))

def create_access_token(tracker_group: int, admin: bool, track: bool, view: bool, days: int, minutes:int):
    with Session(engine) as session:
        group = session.scalar(select(TrackerGroup).where(TrackerGroup.id.is_(tracker_group)))
        assert group is not None # otherwise, there would be no access
        access_code = AccessCode(
            code=generate_new_code(), admin=admin, track=track, view=view, access_range=datetime.timedelta(days=days, minutes=minutes), group=group)
        session.add(access_code)
        session.commit()

def delete_access_code(access_code_id: int):
    with Session(engine) as session:
        access = session.scalar(select(AccessCode).where(AccessCode.id.is_(access_code_id)))
        group_id = access.group_id
        was_admin = access.admin
        if access is None:
            return
        session.delete(access)
        if was_admin:
            other_admins = session.execute(select(func.count()).select_from(AccessCode).where(AccessCode.group_id.is_(group_id)).where(AccessCode.admin.is_(True))).scalar_one()
            if other_admins == 0:
                session.rollback()
                ui.notify("no other admin account defined, cannot delete last one")
                return
        session.commit()

@ui.page("/{access_id}/tracker/{tracker_id}/edit")
def edit_tracker(access_id: str, tracker_id: int):
    with Session(engine) as session:
        tracker = session.scalar(select(Tracker).where(Tracker.id.is_(tracker_id)))
        if not tracker:
            deny()
        else:
            group = tracker.group
            access: Access = get_access(group.id, access_id)
            if not access.admin:
                deny()
            else:
                state_list(tracker)

@ui.refreshable
def state_list(tracker: Tracker):
    with ui.grid(columns="auto auto auto auto auto"):
        ui.label("")
        ui.label("state")
        ui.label("color")
        ui.label("visible")
        ui.label("reorder")

        for i, state in enumerate(tracker.allowed_states):
            ui.label(str(i))
            ui.button(state.name, color=state.color)
            ui.color_input(value=state.color, on_change=lambda e, s=state.id: set_color(s, e.value))
            print(state.visible)
            ui.checkbox("", on_change=lambda e, s=state.id: set_visible(s, e.value), value=state.visible)
            with ui.row():
                ui.button("", icon="arrow_upward", on_click=lambda t=tracker.id, old=i, new=i-1: reorder_state(t, old, new)).set_enabled(i>0)
                ui.button("", icon="arrow_downward", on_click=lambda t=tracker.id, old=i, new=i+1: reorder_state(t, old, new)).set_enabled(i<len(tracker.allowed_states)-1)

        ui.label("")
        state_name = ui.input(label="state name")
        ui.label("")
        ui.button("add", icon="add", color="green", on_click=lambda t=tracker.id, sn=state_name: new_state(t, sn.value))

def new_state(tracker_id: int, state_name: str):
    if not state_name:
        ui.notify("no state name given")
        return
    with Session(engine) as session:
        state = session.scalar(select(State).where(State.tracker_id.is_(tracker_id)).where(State.name.is_(state_name)))
        if state is not None:
            ui.notify("state with this name already exists")
            return
        tracker = session.scalar(select(Tracker).where(Tracker.id.is_(tracker_id)))
        tracker.allowed_states.append(State(name=state_name, tracker_id=tracker_id))
        session.commit()



def reorder_state(tracker_id, old_id: int, new_id: int):
    with Session(engine) as session:
        tracker = session.scalar(select(Tracker).where(Tracker.id.is_(tracker_id)))
        if not tracker:
            return # ignore
        state = tracker.allowed_states.pop(old_id)
        tracker.allowed_states.insert(new_id, state)
        session.commit()
    state_list.refresh()

def set_color(state_id: int, color: str):
    with Session(engine) as session:
        state = session.scalar(select(State).where(State.id.is_(state_id)))
        if not state:
            return # ignore
        state.color=color
        session.commit()
    state_list.refresh()

def set_visible(state_id: int, visible: bool):
    with Session(engine) as session:
        state = session.scalar(select(State).where(State.id.is_(state_id)))
        if not state:
            return # ignore
        state.visible=visible
        print(state.id, state.visible)
        session.commit()
    state_list.refresh()

def log_event(state_id: int):
    with Session(engine) as session:
        state = session.scalar(select(State).where(State.id.is_(state_id)))
        if not state:
            logging.error("no state with id {state_id} found, ignoring")
        else:
            event = Event(state=state, timestamp=datetime.datetime.now())
            session.add_all([event])
        session.commit()

def log_event_manually(state_id: int, date: str, time: str):
    timestamp = datetime.datetime.combine(datetime.date.fromisoformat(date), datetime.time.fromisoformat(time))
    with Session(engine) as session:
        state = session.scalar(select(State).where(State.id.is_(state_id)))
        if not state:
            logging.error("no state with id {state_id} found, ignoring")
        else:
            event = Event(state=state, timestamp=timestamp)
            session.add_all([event])
        session.commit()


@app.get("/{access_id}/{tracker_group}/download")
def download(access_id: str, tracker_group: int):
    access: Access = get_access(tracker_group, access_id)
    with Session(engine) as session:
        group = session.scalar(select(TrackerGroup).where(TrackerGroup.id.is_(tracker_group)))
        if group is None:
            raise "not found"
        else:
            with io.StringIO() as f:
                events = session.scalars(select(Event).join(Event.state).join(State.tracker).join(Tracker.group).where(TrackerGroup.id.is_(tracker_group)).where(Event.timestamp > datetime.datetime.now()-access.access_range).order_by(Event.timestamp))

                for event in events:
                    f.write(f"{event.timestamp.isoformat(timespec='seconds')};{event.state.tracker.name};{event.state.name}\n")
                return PlainTextResponse(f.getvalue(), media_type="text/csv")


def copyable_link(url: str):
    with ui.row().classes('items-center gap-1'):
        copy_btn = ui.icon('content_copy').classes(
            'cursor-pointer text-gray-600 hover:text-black transition-colors'
        )

        link = ui.link(url, url).classes(
            'text-blue-600 no-underline hover:underline'
        )
        link.props('target=_blank')  # open in new tab


        def do_copy():
            ui.run_javascript(f'navigator.clipboard.writeText("{url}")')

        copy_btn.on('click', do_copy)

def copyable_page_link(page_func: str, **kwargs):
    url = app.url_path_for(page_func, **kwargs)
    copyable_link(url)

if __name__ == '__main__':
    ui.run()

