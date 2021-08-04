import psutil
import time
from datetime import datetime
import curses
import argparse
import subprocess

#-t --time 可以指定刷新间隔时间
#-u --unit 可以指定网卡显示的单位

#使用psutil调用传感器太麻烦了，这里自己用命令获取CPU温度了
cmd0 = "cat /sys/class/thermal/thermal_zone0/temp"
#网卡信息从第几行开始显示
prev = 5

def process_shell(cmd):
    # 执行cmd命令，如果成功，返回(0, 'xxx')；如果失败，返回(1, 'xxx')
    res = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) # 使用管道
    result = res.stdout.read()  # 获取输出结果
    res.wait()  # 等待命令执行完成
    res.stdout.close() # 关闭标准输出
    return str(result)

#CPU使用率、CPU频率、CPU温度
def getCPUInfo():
    return str(psutil.cpu_percent()),\
           str(psutil.cpu_freq()[0]),\
           str((int(int(process_shell(cmd0)[2:6])/100)))
#总内存 可用内存 使用内存 内存使用率
def getMemInfo():
    return str(round(psutil.virtual_memory().total/1024/1024)),\
           str(round(psutil.virtual_memory().available/1024/1024)),\
           str(round(psutil.virtual_memory().used/1024/1024)),\
           str(int(psutil.virtual_memory().percent))

def getNetworkData():
    # 获取网卡流量信息
    recv = {}
    sent = {}
    data = psutil.net_io_counters(pernic=True)
    interfaces = data.keys()
    for interface in interfaces:
        recv.setdefault(interface, data.get(interface).bytes_recv)
        sent.setdefault(interface, data.get(interface).bytes_sent)
    return interfaces, recv, sent


def getNetworkRate(num):
    # 计算网卡流量速率
    interfaces, oldRecv, oldSent = getNetworkData()
    time.sleep(num)
    interfaces, newRecv, newSent = getNetworkData()
    networkIn = {}
    networkOut = {}
    for interface in interfaces:
        networkIn.setdefault(interface, float("%.3f" % ((newRecv.get(interface) - oldRecv.get(interface)) / num)))
        networkOut.setdefault(interface, float("%.3f" % ((newSent.get(interface) - oldSent.get(interface)) / num)))
    return interfaces, networkIn, networkOut

def output(num, unit):
    # 将监控输出到终端
    stdscr = curses.initscr()
    curses.start_color()
    curses.noecho()
    curses.cbreak()
    stdscr.clear()
    try:
        interfaces, _, _ = getNetworkData()
        while True:
            _, networkIn, networkOut = getNetworkRate(num)
            currTime = datetime.now()
            timeStr = datetime.strftime(currTime, "%Y-%m-%d %H:%M:%S")
            stdscr.erase()
            stdscr.addstr(0, 0, timeStr)
            #CPU信息
            cpuPer,cpuFreq,cpuTmp = getCPUInfo()
            stdscr.addstr(2,0,"CPU Usage: " + cpuPer + " %")
            stdscr.addstr(3,0,"CPU Freq: " + cpuFreq + " Mhz")
            stdscr.addstr(4,0,"CPU Temp: " + cpuTmp + " ℃")
            #内存信息
            memTotal,memAva,memUsed,memPer = getMemInfo()
            stdscr.addstr(2,32,"Mem Usage: " + memPer + " %")
            stdscr.addstr(3,32,"Mem Used: " + memUsed + " MB / " + memTotal + " MB")
            stdscr.addstr(4,32,"Mem Available: " + memAva + " MB / " + memTotal + " MB")
            #网络信息
            i = 1
            for interface in interfaces:
                if interface != "lo" and bool(1 - interface.startswith("veth")) and bool(
                        1 - interface.startswith("br")) and bool(
                    1 - interface.startswith("蓝牙")) and bool(1 - interface.startswith("VMware")):
                    if unit == "k":
                        netIn = "%12.2fKB/s" % (networkIn.get(interface) / 1024)
                        netOut = "%11.2fKB/s" % (networkOut.get(interface) / 1024)
                    elif unit == "m":
                        netIn = "%12.2fMB/s" % (networkIn.get(interface) / 1024 / 1024)
                        netOut = "%11.2fMB/s" % (networkOut.get(interface) / 1024 / 1024)
                    elif unit == "g":
                        netIn = "%12.3fGB/s" % (networkIn.get(interface) / 1024 / 1024 / 1024)
                        netOut = "%11.3fGB/s" % (networkOut.get(interface) / 1024 / 1024 / 1024)
                    else:
                        netIn = "%12.1fB/s" % networkIn.get(interface)
                        netOut = "%11.1fB/s" % networkOut.get(interface)
                    stdscr.addstr(++prev, (i - 1) * 8, interface)
                    stdscr.addstr(++prev + 1, (i - 1) * 8, "Input:%s" % netIn)
                    stdscr.addstr(++prev + 2, (i - 1) * 8, "Output:%s" % netOut)
                    stdscr.move(++prev + 3, (i - 1) * 8)
                    i += 4
                    stdscr.refresh()
    except KeyboardInterrupt:
        # 还原终端
        curses.echo()
        curses.nocbreak()
        curses.endwin()
    except Exception as e:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        print("ERROR: %s!" % e)
        print("Please increase the terminal size!")
    finally:
        curses.echo()
        curses.nocbreak()
        curses.endwin()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A command for monitoring the hardware! Ctrl + C: Exit")
    parser.add_argument("-t", "--time", type=int, help="the interval time for display", default=1)
    parser.add_argument("-u", "--unit", type=str, choices=["b", "k", "m", "g"],
                        help="the unit for display", default="k")
    args = parser.parse_args()
    num = args.time
    unit = args.unit
    output(num, unit)
