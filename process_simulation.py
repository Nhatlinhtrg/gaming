
from collections import deque

class Process:
    def init(self, pid, steps, creation_time):
        self.pid = pid
        self.steps = steps  # list of tuples (type, duration), type: 'cpu' or 'io'
        self.creation_time = creation_time
        self.current_step = 0
        self.remaining_time = steps[0][1] if steps else 0  # for RR quantum management

        self.waiting_time = 0  # tổng thời gian chờ trong ready queue
        self.last_ready_time = None  # thời điểm vào ready queue để tính chờ

        self.start_time = None  # thời điểm tiến trình bắt đầu lần đầu
        self.finish_time = None  # thời điểm tiến trình kết thúc

    def is_finished(self):
        return self.current_step >= len(self.steps)

    def current_step_type(self):
        if self.is_finished():
            return None
        return self.steps[self.current_step][0]

    def current_step_duration(self):
        if self.is_finished():
            return 0
        return self.steps[self.current_step][1]

    def proceed_step(self, time_used):
        remaining = self.remaining_time - time_used
        if remaining <= 0:
            self.current_step += 1
            if not self.is_finished():
                self.remaining_time = self.steps[self.current_step][1]
            else:
                self.remaining_time = 0
            return True
        else:
            self.remaining_time = remaining
            return False

def fifo_simulation(processes):
    time = 0
    ready_queue = deque()
    io_queue = deque()
    events = []

    processes = sorted(processes, key=lambda p: p.creation_time)
    proc_index = 0
    cpu_busy = False
    current_process = None
    cpu_end_time = 0

    cpu_busy_time = 0  # tổng thời gian CPU bận

    while True:
        while proc_index < len(processes) and processes[proc_index].creation_time <= time:
            p = processes[proc_index]
            ready_queue.append(p)
            p.last_ready_time = time
            events.append(f"[{time}] Process {p.pid} created and added to Ready Queue")
            proc_index += 1

        if cpu_busy and time == cpu_end_time:
            p = current_process
            step_type = p.current_step_type()
            time_used = p.remaining_time
            step_finished = p.proceed_step(time_used)
            events.append(f"[{time}] Process {p.pid} finished {step_type} step")

            cpu_busy = False
            current_process = None

            if step_type == 'cpu':
                if not p.is_finished():
                    if p.current_step_type() == 'io':
                        io_queue.append((p, time + p.current_step_duration()))
                        events.append(f"[{time}] Process {p.pid} moved to IO queue")
                    else:
                        ready_queue.append(p)
                        p.last_ready_time = time
                else:
                    p.finish_time = time
                    events.append(f"[{time}] Process {p.pid} finished all steps")

        io_done = []
        for i, (p, finish_time) in enumerate(io_queue):
            if finish_time <= time:
                io_done.append(i)
                p.proceed_step(p.current_step_duration())
                if not p.is_finished():
                    ready_queue.append(p)
                    p.last_ready_time = time
                    events.append(f"[{time}] Process {p.pid} finished IO and moved to Ready Queue")
                else:
                    p.finish_time = time
                    events.append(f"[{time}] Process {p.pid} finished all steps after IO")

        for i in reversed(io_done):
            io_queue.remove(io_queue[i])

        if not cpu_busy and ready_queue:
            p = ready_queue.popleft()
            if p.start_time is None:
                p.start_time = time
            if p.last_ready_time is not None:
                p.waiting_time += time - p.last_ready_time
                p.last_ready_time = None


            if p.current_step_type() == 'cpu':
                duration = p.remaining_time
                cpu_end_time = time + duration
                cpu_busy = True
                current_process = p
                cpu_busy_time += duration
                events.append(f"[{time}] Process {p.pid} started CPU step for {duration} time units")
            else:
                io_queue.append((p, time + p.current_step_duration()))
                events.append(f"[{time}] Process {p.pid} moved directly to IO queue")

        if not cpu_busy and not ready_queue and not io_queue and proc_index >= len(processes):
            break

        time += 1

    print("FIFO Simulation Events:")
    for e in events:
        print(e)

    print("\n--- FIFO Summary ---")
    total_time = time
    print(f"Total simulation time: {total_time}")
    print(f"Total CPU busy time: {cpu_busy_time}")
    cpu_utilization = (cpu_busy_time / total_time) * 100 if total_time > 0 else 0
    print(f"CPU Utilization: {cpu_utilization:.2f}%")
    for p in processes:
        turnaround = (p.finish_time - p.creation_time) if p.finish_time else None
        print(f"Process {p.pid}: Waiting time in ready queue = {p.waiting_time}, Turnaround time = {turnaround}")

def round_robin_simulation(processes, quantum=30):
    time = 0
    ready_queue = deque()
    io_queue = deque()
    events = []

    processes = sorted(processes, key=lambda p: p.creation_time)
    proc_index = 0
    cpu_busy = False
    current_process = None
    cpu_end_time = 0

    cpu_busy_time = 0

    while True:
        while proc_index < len(processes) and processes[proc_index].creation_time <= time:
            p = processes[proc_index]
            ready_queue.append(p)
            p.last_ready_time = time
            events.append(f"[{time}] Process {p.pid} created and added to Ready Queue")
            proc_index += 1

        if cpu_busy and time == cpu_end_time:
            p = current_process
            step_type = p.current_step_type()
            time_used = min(quantum, p.remaining_time)
            step_finished = p.proceed_step(time_used)

            if step_finished:
                events.append(f"[{time}] Process {p.pid} finished {step_type} step")
                cpu_busy = False
                current_process = None
                if step_type == 'cpu':
                    if not p.is_finished():
                        if p.current_step_type() == 'io':
                            io_queue.append((p, time + p.current_step_duration()))
                            events.append(f"[{time}] Process {p.pid} moved to IO queue")
                        else:
                            ready_queue.append(p)
                            p.last_ready_time = time
                    else:
                        p.finish_time = time
                        events.append(f"[{time}] Process {p.pid} finished all steps")
            else:
                events.append(f"[{time}] Process {p.pid} quantum expired, remaining time {p.remaining_time}")
                cpu_busy = False
                current_process = None
                ready_queue.append(p)

        io_done = []
        for i, (p, finish_time) in enumerate(io_queue):
            if finish_time <= time:
                io_done.append(i)
                p.proceed_step(p.current_step_duration())
                if not p.is_finished():
                    ready_queue.append(p)
                    p.last_ready_time = time
                    events.append(f"[{time}] Process {p.pid} finished IO and moved to Ready Queue")
                else:
                    p.finish_time = time
                    events.append(f"[{time}] Process {p.pid} finished all steps after IO")

        for i in reversed(io_done):
            io_queue.remove(io_queue[i])


        if not cpu_busy and ready_queue:
            p = ready_queue.popleft()
            if p.start_time is None:
                p.start_time = time
            if p.last_ready_time is not None:
                p.waiting_time += time - p.last_ready_time
                p.last_ready_time = None

            if p.current_step_type() == 'cpu':
                duration = min(quantum, p.remaining_time)
                cpu_end_time = time + duration
                cpu_busy = True
                current_process = p
                cpu_busy_time += duration
                events.append(f"[{time}] Process {p.pid} started CPU step for {duration} time units")
            else:
                io_queue.append((p, time + p.current_step_duration()))
                events.append(f"[{time}] Process {p.pid} moved directly to IO queue")

        if not cpu_busy and not ready_queue and not io_queue and proc_index >= len(processes):
            break

        time += 1

    print("\nRound-Robin Simulation Events:")
    for e in events:
        print(e)

    print("\n--- Round-Robin Summary ---")
    total_time = time
    print(f"Total simulation time: {total_time}")
    print(f"Total CPU busy time: {cpu_busy_time}")
    cpu_utilization = (cpu_busy_time / total_time) * 100 if total_time > 0 else 0
    print(f"CPU Utilization: {cpu_utilization:.2f}%")
    for p in processes:
        turnaround = (p.finish_time - p.creation_time) if p.finish_time else None
        print(f"Process {p.pid}: Waiting time in ready queue = {p.waiting_time}, Turnaround time = {turnaround}")

# Ví dụ 2 tiến trình
p1 = Process('id_First', [('cpu',20), ('io',20), ('cpu',10)], 0)
p2 = Process('id_Second', [('cpu',10), ('io',10), ('cpu',10)], 10)

# Tạo bản sao để chạy riêng 2 thuật toán
processes1 = [Process(p.pid, p.steps, p.creation_time) for p in [p1, p2]]
processes2 = [Process(p.pid, p.steps, p.creation_time) for p in [p1, p2]]

fifo_simulation(processes1)
round_robin_simulation(processes2, quantum=30)
