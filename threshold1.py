import requests
import concurrent.futures
import time
import threading
import subprocess
import json
import numpy as np
import random
import os

# define result path
result_dir = "./static_result/result79/"

# delay modify = average every x delay (x = 10, 50, 100)
# request rate r
data_rate = 50  # use static request rate
use_tm = 1  # use dynamic traffi4
error_rate = 0.2   # 0.2/0.5

## initial
request_num = []
simulation_time = 300  # 300 s  # 3600s
cpus = 0.5
replica = 2

request_n = simulation_time
change = 0   # 1 if take action / 0 if init or after taking action
send_finish = 0
timestamp = 0
RFID = 0

ip = "192.168.99.121"  # app_mn1
ip1 = "192.168.99.122"  # app_mn2
url = "http://" + ip + ":666/~/mn-cse/mn-name/AE1/"


## 8 stage
stage = ["RFID_Container_for_stage0", "RFID_Container_for_stage1", "Liquid_Level_Container", "RFID_Container_for_stage2",
         "Color_Container", "RFID_Container_for_stage3", "Contrast_Data_Container", "RFID_Container_for_stage4"]



# check result directory
if os.path.exists(result_dir):
    print("Deleting existing result directory...")
    raise SystemExit  # end process

# build dir
os.mkdir(result_dir)

# store setting
path = result_dir + "setting.txt"
f = open(path, 'a')
data = 'data_rate: ' + str(data_rate) + '\n'
data += 'use_tm: ' + str(use_tm) + '\n'
data += 'simulation_time ' + str(simulation_time) + '\n'
data += 'cpus: ' + str(cpus) + '\n'
data += 'replica ' + str(replica) + '\n'
f.write(data)
f.close()

if use_tm:
    #   Modify the workload path if it is different
    f = open('request/request6.txt')

    for line in f:
        if len(request_num) < request_n:

            request_num.append(int(float(line)))
else:
    request_num = [data_rate for i in range(simulation_time)]

print('request_num:: ', len(request_num))


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
    try:
        response = requests.post(url, headers=headers, json=data, timeout=0.1)
        response = str(response.status_code)
    except requests.exceptions.Timeout:
        response = "timeout"


    return response


def store_cpu(start_time, woker_name):
    global timestamp, cpus, change

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
                if float(cpu) > 0:
                    final_time = time.time()
                    t = final_time - start_time
                    path = result_dir + name + "_cpu.txt"
                    f = open(path, 'a')
                    data = str(timestamp) + ' ' + str(t) + ' '
                    # for d in state_u:
                    data = data + str(cpu) + ' ' + '\n'
                    f.write(data)
                    f.close()


def store_rt(timestamp, response, rt):
    path = result_dir + "app_mn1_response.txt"
    f = open(path, 'a')
    data = str(timestamp) + ' ' + str(response) + ' ' + str(rt) + '\n'
    f.write(data)
    f.close()

# sned request to app_mn2 app_mnae1 app_mnae2
def store_rt2():
    global timestamp, send_finish, change

    path1 = result_dir + "/app_mn2_response.txt"
    path2 = result_dir + "/app_mnae1_response.txt"
    path3 = result_dir + "/app_mnae2_response.txt"

    while True:
        if change == 0:
            f1 = open(path1, 'a')
            f2 = open(path2, 'a')
            f3 = open(path3, 'a')
            RFID = random.randint(0, 100000000)
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                headers = {"X-M2M-Origin": "admin:admin", "Content-Type": "application/json;ty=4"}
                data = {
                    "m2m:cin": {
                        "con": "true",
                        "cnf": "application/json",
                        "lbl": "req",
                        "rn": str(RFID),
                    }
                }

                # URL 1
                url = "http://" + ip1 + ":777/~/mn-cse/mn-name/AE2/Control_Command_Container"
                try:
                    s_time = time.time()
                    future = executor.submit(requests.post, url, headers=headers, json=data)
                    response = future.result()
                    response_time1 = time.time() - s_time
                    response1 = str(response.status_code)
                except requests.exceptions.Timeout:
                    response1 = "timeout"
                    response_time1 = 0.5

                # # URL 2
                try:
                    s_time = time.time()
                    future = executor.submit(requests.post, "http://" + ip + ":1111/test", headers=headers, json=data)
                    response = future.result()
                    response_time2 = time.time() - s_time
                    response2 = str(response.status_code)
                except requests.exceptions.Timeout:
                    response2 = "timeout"
                    response_time1 = 0.5

                # # URL 3
                try:
                    s_time = time.time()
                    future = executor.submit(requests.post, "http://" + ip1 + ":2222/test", headers=headers, json=data)
                    response = future.result()
                    response_time3 = time.time() - s_time
                    response3 = str(response.status_code)
                except requests.exceptions.Timeout:
                    response3 = "timeout"
                    response_time3 = 0.5

                data1 = str(timestamp) + ' ' + str(response1) + ' ' + str(response_time1) + '\n'
                data2 = str(timestamp) + ' ' + str(response2) + ' ' + str(response_time2) + '\n'
                data3 = str(timestamp) + ' ' + str(response3) + ' ' + str(response_time3) + '\n'
                f1.write(data1)
                f2.write(data2)
                f3.write(data3)
            time.sleep(1)

            if send_finish == 1:
                f1.close()
                f2.close()
                f3.close()
                break


def send_request(url, stage, request_num, start_time):
    global change, send_finish
    global timestamp, use_tm, RFID

    error = 0

    for i in request_num:

        print("timestamp: ", timestamp)
        exp = np.random.exponential(scale=1 / i, size=i)
        tmp_count = 0
        for j in range(i):
            try:
                # change stage
                url1 = url + stage[(tmp_count * 10 + j) % 8]
                if error_rate > random.random():
                    content = "false"
                else:
                    content = "true"
                s_time = time.time()
                response = post_url(url1, RFID, content)
                # print(response)
                t_time = time.time()
                rt = t_time - s_time
                store_rt(timestamp, response, rt)
                RFID += 1

            except:
                print("eror")
                error += 1

            if use_tm == 1:
                time.sleep(exp[tmp_count])
                tmp_count += 1

            else:
                time.sleep(1 / i)  # send requests every 1s

        timestamp += 1

    final_time = time.time()
    alltime = final_time - start_time
    print('time:: ', alltime)
    send_finish = 1


def manual_action():
    global cpus, T_max, type, change, send_finish, replicas
    global timestamp

    change_check = [0, 0, 0, 0, 0, 0, 1]
    change_type = 2  # 1 : change cpus 2: change replica
    while True:
        if send_finish == 1:
            break
        print(timestamp)
        if ((timestamp % 50) == 0) and (change_type == 1) and (timestamp != 0):
            idx = int(timestamp / 50)
            if change_check[idx] == 0:
                change = 1
                cpus += 0.1
                cpus = round(cpus, 1)
                cmd = "sudo docker-machine ssh default docker service update --limit-cpu " + str(cpus) + " app_mn1"
                returned_text = subprocess.check_output(cmd, shell=True)
                change_check[idx] = 1
                print('change cpus to ', cpus)
        if (timestamp == 150) and (change_type == 2) and (timestamp != 0):
            idx = int(timestamp/50)
            if change_check[idx] == 0:
                change = 1
                replicas += 1
                change_check[idx] = 1
                cmd = "sudo docker-machine ssh default docker service scale app_mn1=" + str(replicas)
                returned_text = subprocess.check_output(cmd, shell=True)
                # print('change replicas to ', replicas)


start_time = time.time()

t1 = threading.Thread(target=send_request, args=(url, stage, request_num, start_time, ))
t2 = threading.Thread(target=store_cpu, args=(start_time, 'worker',))
t3 = threading.Thread(target=store_cpu, args=(start_time, 'worker1',))
t4 = threading.Thread(target=store_rt2)
# t7 = threading.Thread(target=manual_action)

t1.start()
t2.start()
t3.start()
t4.start()
# t5.start()
# t6.start()
# t7.start()

t1.join()
t2.join()
t3.join()
t4.join()
# t5.join()
# t6.join()
# t7.join()
