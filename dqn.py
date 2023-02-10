#  troch
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

import requests
import time
import threading
import subprocess
import json
import numpy as np
import random
import statistics
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

# request rate r
r = 50      # if not use_tm
use_tm = 1  # if use_tm
error_rate = 0.2  # 0.2/0.5

# initial setting (threshold setting) # no use now
T_max = 0.065  # t_max violation
T_min = 0.055
set_tmin = 1  # 1 if setting tmin
cpus = 0.5  # initial cpus
replicas = 1  # initial replica

## initial
request_num = []
simulation_time = 3600  # 300 s  # or 3600s
request_n = simulation_time
change = 0   # 1 if take action / 0 if init or after taking action
reset_complete = 0
send_finish = 0
timestamp = 0  # plus 1 in funcntion : send_request
RFID = 0  # choose random number for data


## Learning parameter
# S ={k, u , c}
# k (replica): 1 ~ 3                          actual value : same
# u (cpu utilization) : 0.0, 0.1 0.2 ...1     actual value : 0 ~ 100
# c (used cpus) : 0.1 0.2 ... 1               actual value : same
# action_space = ['-r', -1, 0, 1, 'r']
total_episodes = 5       # Total episodes
learning_rate = 0.01          # Learning rate
# max_steps = 50               # Max steps per episode
# Exploration parameters
gamma = 0.9                 # Discounting rate
max_epsilon = 1
min_epsilon = 0.1
epsilon_decay = 1/300

## 7/8 stage
stage = ["RFID_Container_for_stage0", "RFID_Container_for_stage1", "Liquid_Level_Container", "RFID_Container_for_stage2",
         "Color_Container", "RFID_Container_for_stage3", "Contrast_Data_Container", "RFID_Container_for_stage4"]

if use_tm:
    f = open('/home/user/flask_test/client/request/request6.txt')

    for line in f:
        if len(request_num) < request_n:

            request_num.append(int(float(line)))
else:
    request_num = [r for i in range(simulation_time)]


print("request_num:: ", len(request_num), "simulation_time:: ", simulation_time)


class Env:

    def __init__(self, service_name="app_mn1"):

        self.service_name = service_name
        self.cpus = 0.5
        self.replica = 1
        self.cpu_utilization = 0.0
        self.action_space = ['-r', '-1', '0', '1', 'r']
        self.n_actions = len(self.action_space)

        # Need modify if ip change
        self.url_list = ["http://192.168.99.115:666/~/mn-cse/mn-name/AE1/RFID_Container_for_stage4", "http://192.168.99.116:777/~/mn-cse/mn-name/AE2/Control_Command_Container", "http://192.168.99.115:1111/test", "http://192.168.99.116:2222/test"]


    def reset(self):
        cmd = "sudo docker-machine ssh default docker stack rm app"
        subprocess.check_output(cmd, shell=True)
        cmd1 = "sudo docker-machine ssh default docker stack deploy --compose-file docker-compose.yml app"
        subprocess.check_output(cmd1, shell=True)
        time.sleep(60)

    def get_response_time(self):
        global RFID
        path1 = "result/" + self.service_name + "_response.txt"

        f1 = open(path1, 'a')

        headers = {"X-M2M-Origin": "admin:admin", "Content-Type": "application/json;ty=4"}
        data = {
            "m2m:cin": {
                "con": "true",
                "cnf": "application/json",
                "lbl": "req",
                "rn": str(RFID + 10000),
            }
        }
        # URL
        service_name_list = ["app_mn1", "app_mn2"]
        url = self.url_list[service_name_list.index(self.service_name)]
        start = time.time()
        response = requests.post(url, headers=headers, json=data)
        end = time.time()
        response_time = end - start
        data1 = str(timestamp) + ' ' + str(response_time) + ' ' + str(self.cpus) + ' ' + str(self.replica) + '\n'
        f1.write(data1)
        f1.close()
        return response_time

    def get_cpu_utilization(self):
        path = "result/" + self.service_name + '_cpu.txt'
        try:
            f = open(path, "r")
            cpu = []
            time = []
            for line in f:
                s = line.split(' ')
                time.append(float(s[0]))
                cpu.append(float(s[2]))

            last_cpu = cpu[-1]
            f.close()

            return last_cpu
        except:
            print('cant open')

    def discretize_cpu_value(self, value):
        return int(round(value / 10))

    def step(self, action_index):
        global timestamp, send_finish, RFID, change
        action = self.action_space[action_index]
        if action == '-r':
            if self.replica > 1:
                self.replica -= 1
                change = 1
                cmd = "sudo docker-machine ssh default docker service scale " + self.service_name + "=" + str(self.replica)
                returned_text = subprocess.check_output(cmd, shell=True)

        if action == '-1':
            if self.cpus >= 0.5:
                self.cpus -= 0.1
                self.cpus = round(self.cpus, 1)  # ex error:  0.7999999999999999
                change = 1
                cmd = "sudo docker-machine ssh default docker service update --limit-cpu " + str(self.cpus) + " " + self.service_name
                returned_text = subprocess.check_output(cmd, shell=True)

        if action == '1':
            if self.cpus < 1:
                self.cpus += 0.1
                self.cpus = round(self.cpus, 1)
                change = 1
                cmd = "sudo docker-machine ssh default docker service update --limit-cpu " + str(self.cpus) + " " + self.service_name
                returned_text = subprocess.check_output(cmd, shell=True)

        if action == 'r':
            if self.replica < 3:
                self.replica += 1
                change = 1
                cmd = "sudo docker-machine ssh default docker service scale " + self.service_name + "=" + str(self.replica)
                returned_text = subprocess.check_output(cmd, shell=True)

        time.sleep(30)
        # change = 0
        response_time_list = []
        for i in range(5):
            time.sleep(3)
            response_time_list.append(self.get_response_time())

        # avg_response_time = sum(response_time_list)/len(response_time_list)
        median_response_time = statistics.median(response_time_list)
        median_response_time = median_response_time*1000  # 0.05s -> 50ms
        if median_response_time >= 50:
            Rt = 50
        else:
            Rt = median_response_time
        if self.service_name == "app_mn1":
            t_max = 25
        elif self.service_name == "app_mn2":
            t_max = 15
        else:
            t_max = 5

        if median_response_time < t_max:
            c_perf = 0
        else:
            tmp_d = 1.4 ** (50 / t_max)
            tmp_n = 1.4 ** (Rt / t_max)
            c_perf = tmp_n / tmp_d

        c_res = (self.replica*self.cpus)/3   # replica*self.cpus / Kmax
        next_state = []
        # k, u, c # r
        self.cpu_utilization = self.get_cpu_utilization()
        u = self.discretize_cpu_value(self.cpu_utilization)
        next_state.append(self.replica)
        next_state.append(u/10)
        next_state.append(self.cpus)
        next_state = np.ndarray(next_state)
        # state.append(req)
        done = False
        w_pref = 0.5
        w_res = 0.5
        reward = -(w_pref * c_perf + w_res * c_res)
        # print("step_over_next_state: ", next_state)
        return next_state, reward, done


class ReplayBuffer:
    """A simple numpy replay buffer."""

    def __init__(self, obs_dim: int, size: int, batch_size: int = 32):
        self.obs_buf = np.zeros([size, obs_dim], dtype=np.float32)
        self.next_obs_buf = np.zeros([size, obs_dim], dtype=np.float32)
        self.acts_buf = np.zeros([size], dtype=np.float32)
        self.rews_buf = np.zeros([size], dtype=np.float32)
        self.done_buf = np.zeros(size, dtype=np.float32)
        self.max_size, self.batch_size = size, batch_size
        self.ptr, self.size, = 0, 0

    def store(
        self,
        obs: np.ndarray,
        act: np.ndarray,
        rew: float,
        next_obs: np.ndarray,
        done: bool,
    ):
        self.obs_buf[self.ptr] = obs
        self.next_obs_buf[self.ptr] = next_obs
        self.acts_buf[self.ptr] = act
        self.rews_buf[self.ptr] = rew
        self.done_buf[self.ptr] = done
        self.ptr = (self.ptr + 1) % self.max_size
        self.size = min(self.size + 1, self.max_size)

    def sample_batch(self) -> Dict[str, np.ndarray]:
        idxs = np.random.choice(self.size, size=self.batch_size, replace=False)
        return dict(obs=self.obs_buf[idxs],
                    next_obs=self.next_obs_buf[idxs],
                    acts=self.acts_buf[idxs],
                    rews=self.rews_buf[idxs],
                    done=self.done_buf[idxs])

    def __len__(self) -> int:
        return self.size


class Network(nn.Module):
    def __init__(self, in_dim: int, out_dim: int):
        """Initialization."""
        super(Network, self).__init__()

        self.layers = nn.Sequential(
            nn.Linear(in_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, out_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward method implementation."""
        return self.layers(x)


class DQNAgent:
    def __init__(
            self,
            env,  # need change
            memory_size: int,
            batch_size: int,
            target_update: int,
            epsilon_decay: float,
            max_epsilon: float = 1.0,
            min_epsilon: float = 0.1,
            gamma: float = 0.99,
    ):

        # obs_dim = env.observation_space.shape[0]
        # action_dim = env.action_space.n
        obs_dim = 4  # S = ={𝑘, 𝑢, 𝑐,𝑟}
        action_dim = 5  # 𝐴={−𝑟, −1,  0,  1,  𝑟}

        self.env = Env()
        self.memory = ReplayBuffer(obs_dim, memory_size, batch_size)
        self.batch_size = batch_size
        self.epsilon = max_epsilon
        self.epsilon_decay = epsilon_decay
        self.max_epsilon = max_epsilon
        self.min_epsilon = min_epsilon
        self.target_update = target_update
        self.gamma = gamma

        # device: cpu / gpu
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        print(self.device)
        print(self.env.cpus)
        # networks: dqn, dqn_target
        self.dqn = Network(obs_dim, action_dim).to(self.device)
        self.dqn_target = Network(obs_dim, action_dim).to(self.device)
        self.dqn_target.load_state_dict(self.dqn.state_dict())
        self.dqn_target.eval()

        # optimizer
        self.optimizer = optim.Adam(self.dqn.parameters())

        # transition to store in memory
        self.transition = list()

        # mode: train / test
        self.is_test = False

    def select_action(self, state: np.ndarray) -> np.ndarray:
        """Select an action from the input state."""
        # epsilon greedy policy
        if self.epsilon > np.random.random():
            # selected_action = self.env.action_space.sample()  #need change
            selected_action = random.sample(self.env.action_space, 1)  # need change
        else:
            selected_action = self.dqn(
                torch.FloatTensor(state).to(self.device)
            ).argmax()
            selected_action = selected_action.detach().cpu().numpy()

        if not self.is_test:
            self.transition = [state, selected_action]

        return selected_action

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, np.float64, bool]:
        """Take an action and return the response of the env."""
        # next_state, reward, done, _ = self.env.step(action)
        next_state, reward, done = self.env.step(action)

        if not self.is_test:
            self.transition += [reward, next_state, done]
            self.memory.store(*self.transition)

        return next_state, reward, done

    def update_model(self) -> torch.Tensor:
        """Update the model by gradient descent."""
        samples = self.memory.sample_batch()

        loss = self._compute_dqn_loss(samples)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def train(self, num_frames: int, plotting_interval: int = 200):
        """Train the agent."""
        self.is_test = False

        state = self.env.reset()
        update_cnt = 0
        epsilons = []
        losses = []
        scores = []
        score = 0

        for frame_idx in range(1, num_frames + 1):
            action = self.select_action(state)
            next_state, reward, done = self.step(action)

            state = next_state
            score += reward

            # if episode ends
            if done:
                state = self.env.reset()
                scores.append(score)
                score = 0

            # if training is ready
            if len(self.memory) >= self.batch_size:
                loss = self.update_model()
                losses.append(loss)
                update_cnt += 1

                # linearly decrease epsilon
                self.epsilon = max(
                    self.min_epsilon, self.epsilon - (
                            self.max_epsilon - self.min_epsilon
                    ) * self.epsilon_decay
                )
                epsilons.append(self.epsilon)

                # if hard update is needed
                if update_cnt % self.target_update == 0:
                    self._target_hard_update()

            # plotting
            if frame_idx % plotting_interval == 0:
                self._plot(frame_idx, scores, losses, epsilons)

        # self.env.close()

    def test(self) -> List[np.ndarray]:
        """Test the agent."""
        self.is_test = True

        state = self.env.reset()
        done = False
        score = 0

        frames = []

        print("score: ", score)
        self.env.close()

        return frames

    def _compute_dqn_loss(self, samples: Dict[str, np.ndarray]) -> torch.Tensor:
        """Return dqn loss."""
        device = self.device  # for shortening the following lines
        state = torch.FloatTensor(samples["obs"]).to(device)
        next_state = torch.FloatTensor(samples["next_obs"]).to(device)
        action = torch.LongTensor(samples["acts"].reshape(-1, 1)).to(device)
        reward = torch.FloatTensor(samples["rews"].reshape(-1, 1)).to(device)
        done = torch.FloatTensor(samples["done"].reshape(-1, 1)).to(device)

        # G_t   = r + gamma * v(s_{t+1})  if state != Terminal
        #       = r                       otherwise
        curr_q_value = self.dqn(state).gather(1, action)
        next_q_value = self.dqn_target(
            next_state
        ).max(dim=1, keepdim=True)[0].detach()
        mask = 1 - done
        target = (reward + self.gamma * next_q_value * mask).to(self.device)

        # calculate dqn loss
        loss = F.smooth_l1_loss(curr_q_value, target)

        return loss

    def _target_hard_update(self):
        """Hard update: target <- local."""
        self.dqn_target.load_state_dict(self.dqn.state_dict())

    def _plot(
            self,
            frame_idx: int,
            scores: List[float],
            losses: List[float],
            epsilons: List[float],
    ):
        """Plot the training progresses."""
        clear_output(True)
        plt.figure(figsize=(20, 5))
        plt.subplot(131)
        plt.title('frame %s. score: %s' % (frame_idx, np.mean(scores[-10:])))
        plt.plot(scores)
        plt.subplot(132)
        plt.title('loss')
        plt.plot(losses)
        plt.subplot(133)
        plt.title('epsilons')
        plt.plot(epsilons)
        plt.show()




def post_url(url, RFID, content):

    headers = {"X-M2M-Origin": "admin:admin", "Content-Type": "application/json;ty=4"}
    data = {
        "m2m:cin": {
            "con": content,
            "cnf": "application/json",
            "lbl": "req",
            "rn": str(RFID),
        }
    }
    response = requests.post(url, headers=headers, json=data)

    return response


def store_cpu(start_time, woker_name):
    global timestamp, cpus, change
    # time.sleep(70)  # wait environment start
    cmd = "sudo docker-machine ssh " + woker_name + " docker stats --all --no-stream --format \\\"{{ json . }}\\\" "
    while True:

        if send_finish == 1:
            break
        if change == 0:
            returned_text = subprocess.check_output(cmd, shell=True)
            my_data = returned_text.decode('utf8')
            # print(my_data.find("CPUPerc"))
            my_data = my_data.split("}")
            # state_u = []
            for i in range(len(my_data) - 1):
                # print(my_data[i]+"}")
                my_json = json.loads(my_data[i] + "}")
                name = my_json['Name'].split(".")[0]
                cpu = my_json['CPUPerc'].split("%")[0]
                # state_u.append(cpu)
                final_time = time.time()
                t = final_time - start_time
                path = "result/output_cpu_" + name + ".txt"
                f = open(path, 'a')
                data = str(timestamp) + ' ' + str(t) + ' '
                # for d in state_u:
                data = data + str(cpu) + ' ' + '\n'

                f.write(data)
                f.close()


def send_request(stage,request_num, start_time, total_episodes):
    global change, send_finish, reset_complete
    global timestamp, use_tm, RFID
    error = 0
    for episode in range(total_episodes):
        print("reset envronment")
        reset()  # reset Environment
        reset_complete = 1
        send_finish = 0
        timestamp = 0
        for i in request_num:
            print("timestamp: ", timestamp)
            exp = np.random.exponential(scale=1 / i, size=i)
            tmp_count = 0
            if change == 1:
                print('change!')
                time.sleep(30)
                change = 0
            for j in range(i):
                try:
                    s_time = time.time()
                    # Need modify if ip change
                    url = "http://192.168.99.115:666/~/mn-cse/mn-name/AE1/"
                    # change stage
                    url1 = url + stage[(i*10+j) % 8]
                    if error_rate > random.random():
                        content = "false"
                    else:
                        content = "true"
                    response = post_url(url1, RFID, content)
                    # print(response)
                    t_time = time.time()
                    rt = t_time - s_time
                    # store_rt(timestamp, rt)
                    RFID += 1

                except:
                    error += 1
                    # print(response.json())
                    f1 = open("error.txt", 'a')
                    f1.close()
                    # print('Cant Send Request!')
                    time.sleep(2)

                if use_tm == 1:
                    time.sleep(exp[tmp_count])
                    tmp_count += 1

                else:
                    time.sleep(1/i)  # send requests every 1s
            timestamp += 1
    send_finish = 1
    final_time = time.time()
    alltime = final_time - start_time
    print('time:: ', alltime)


# reset Environment
def reset():
    cmd = "sudo docker-machine ssh default docker stack rm app"
    subprocess.check_output(cmd, shell=True)
    cmd1 = "sudo docker-machine ssh default docker stack deploy --compose-file docker-compose.yml app"
    subprocess.check_output(cmd1, shell=True)
    time.sleep(70)


def store_reward(service_name, reward):
    # Convert the list to a string
    data = '\n'.join(str(x) for x in reward)

    # Write the string to a text file
    path = service_name + "reward.txt"
    f = open(path, 'w')
    f.write(data)


def q_learning(total_episodes, learning_rate, gamma, max_epsilon, min_epsilon, epsilon_decay, service_name):
    global timestamp, simulation_time, change, RFID, send_finish

    env = Env(service_name)
    actions = list(range(env.n_actions))
    RL = QLearningTable(actions, learning_rate, gamma, max_epsilon, min_epsilon, epsilon_decay)
    all_rewards = []
    step = 0
    init_state = [1, 0.0, 0.5]

    for episode in range(total_episodes):
        # initial observation
        state = init_state
        rewards = []  # record reward every episode
        while True:
            if ((timestamp - 1) % 30) == 0:
                print(service_name, "step: ", step, "---------------")
                # RL choose action based on state
                action = RL.choose_action(state)
                print("action: ", action)
                # change = 1
                # RL take action and get next state and reward
                next_state, reward, done = env.step(action)

                if timestamp == (simulation_time-1):
                    done = True

                print("next_state: ", next_state, "reward: ", reward)
                rewards.append(reward)
                # RL learn from this transition
                RL.learn(state, action, reward, next_state, done)

                # swap state
                state = next_state
                step += 1
                if done:
                    avg_rewards = sum(rewards)/len(rewards)
                    break

        all_rewards.append(avg_rewards)
    # episode end
    print("service:", service_name, all_rewards)
    store_reward(service_name, all_rewards)


start_time = time.time()

t1 = threading.Thread(target=send_request, args=(stage, request_num, start_time, total_episodes, ))
t2 = threading.Thread(target=store_cpu, args=(start_time, 'worker',))
t3 = threading.Thread(target=store_cpu, args=(start_time, 'worker1',))
t4 = threading.Thread(target=q_learning, args=(total_episodes, learning_rate, gamma, max_epsilon, min_epsilon, epsilon_decay, 'app_mn1', ))
t5 = threading.Thread(target=q_learning, args=(total_episodes, learning_rate, gamma, max_epsilon, min_epsilon, epsilon_decay, 'app_mn2', ))


t1.start()
t2.start()
t3.start()
t4.start()
t5.start()


t1.join()
t2.join()
t3.join()
t4.join()
t5.join()
