import socket
import threading
import os
import time
import hashlib


class Node:
    def __init__(self, host, port):
        self.stop = False
        self.host = host
        self.port = port
        self.M = 16
        self.N = 2**self.M
        self.key = self.hasher(host+str(port))
        # You will need to kill this thread when leaving, to do so just set self.stop = True
        threading.Thread(target = self.listener).start()
        self.files = []
        self.join_bool = False
        self.backUpFiles = []
        self.position = ()
        self.succ_changed_bool = False

        self.file_tuple = ()
        self.succ_succ = ()
        self.get_tuple = ()

        self.succ_change = False

        self.file_rehash_bool = False
        self.getfunc_file = ()
        self.file_bool = False
        self.file_curr_node = ()
        self.leave_bool = False

        self.pinging_bool = False
        self.num_pings = 0

        self.joinedx = False
        self.join_one_node = False

        if not os.path.exists(host+"_"+str(port)):
            os.mkdir(host+"_"+str(port))
        '''
        ------------------------------------------------------------------------------------
        DO NOT EDIT ANYTHING ABOVE THIS LINE
        '''
        # Set value of the following variables appropriately to pass Intialization test
        self.successor = (self.host, self.port)
        self.predecessor = (self.host, self.port)
        # additional state variables


    def hasher(self, key):
        '''nn'''
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.N

    def handleConnection(self, client, addr):
        '''nn'''
        incoming_message = client.recv(1024).decode('utf-8')
        message_list = incoming_message.split()

        if message_list[0] =="lookup":
            client.close()
            one_node = False

            if self.successor == (self.host, self.port):
                one_node = True
            else:
                one_node = False

            if one_node:
                h_o = str(self.host)
                p_o = str(self.port)
                message = "1_person" + " " + h_o + " " + p_o
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                soc.connect((message_list[1], int(message_list[2])))
                soc.send(message.encode('utf-8'))
                soc.close()

            elif not one_node:
                tuple_ret = self.lookup(int(message_list[3]), (message_list[1], int(message_list[2])))

                ans_check = False

                if tuple_ret != (" ", 0):
                    ans_check = True
                else:
                    ans_check = False

                if ans_check:
                    msg_type = "ans_found" 
                    arg1 = str(tuple_ret[0])
                    arg2 = str(tuple_ret[1])
                    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    message = msg_type + " "+ arg1 + " "+ arg2
                    soc.connect((message_list[1], int(message_list[2])))
                    soc.send(message.encode('utf-8'))
                    soc.close()

        ############################################# ping statements part 1
        # new node will recv this from old node

        ###### ping new attempt

        if message_list[0] == "dead_ping":
            pred1 = message_list[1]
            pred2 = int(message_list[2])
            self.predecessor = (pred1 , pred2)
            msg = ""
            if message_list[3] == "no":
                msg = "alive"
            else:
                msg = "not_alive"

           
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(self.predecessor)
            suc0 = str(self.successor[0])
            suc1 = str(self.successor[1]) 
            message = "suc_suc_change_ping" +" "+ suc0 + " "+ suc1 + " "+ msg
            conn.send(message.encode('utf-8'))
            conn.close()
            client.close()

        ################################################################ Join statements

        if message_list[0] == "ans_found":
            client.close()
            ans1 = message_list[1]
            ans2 = int(message_list[2])
            self.position = (ans1, ans2)


        if message_list[0] == "1_person" :
            ans1 = message_list[1]
            ans2 = int(message_list[2])
            client.close()

            self.position = (ans1, ans2)
            self.join_bool = True
           


        if message_list[0] == "sec_node_pred":
            
            self.predecessor = (str(message_list[1]), int(message_list[2]))

            s_1 = str(message_list[1])
            s_2 = int(message_list[2])

            self.successor = (s_1, s_2)
            client.close()

        if message_list[0] == "join_change_succ1":
            s_1 = str(message_list[1])
            s_2 = int(message_list[2])

            self.successor = (s_1, s_2)

            #self.successor = (message_list[1], int(message_list[2]))
            _curr_node = False
            send_msg = False
            message = "change_pred_1" + " " + str(self.host) + " " + str(self.port)
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if send_msg:
                _curr_node = True

            soc.connect(self.successor)
            soc.send(message.encode('utf-8'))
            soc.close()
            client.close()

        if message_list[0] == "join_change_pred":
            ex_pred = self.predecessor
            p_1 = message_list[1]
            p_2 = int(message_list[2])

            self.predecessor = (p_1, p_2)

            succ1 = str(self.successor[0])
            succ2 = str(self.successor[1])

            message = "succ_succ" + " "+ succ1 + " " + succ2
            client.send(message.encode('utf-8'))
            client.close()

            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pred1 = str(self.predecessor[0])
            pred2 = str(self.predecessor[1])
            message = "join_change_succ1" + " " + pred1 + " " + pred2
            soc.connect(ex_pred)
            soc.send(message.encode('utf-8'))
            soc.close()

        if message_list[0] == "change_pred_1":
            pred1 = str(message_list[1])
            pred2 = int(message_list[2])
            self.predecessor = (pred1, pred2)
            client.close()

    ############################################# ping part 2
        if message_list[0] == "alive_ping":
            message = ""
            if message_list[3] == "yes":
                message = "alive"
            else:
                message = "not_alive"

            client.send(message.encode('utf-8'))
            client.close()

        if message_list[0] == "suc_suc_change_ping":
            s_1 = message_list[1]
            s_2 = int(message_list[2])

            self.succ_succ = (s_1, s_2)
            client.close()

    ############################################################## file put statements
        if message_list[0] == "put_backup":
            stored = str(message_list[1])
            self.backUpFiles.append(stored)
            client.close()

        if message_list[0] =="lookup_file":
            client.close()

            file_name = message_list[1]
            curr_addr = (message_list[3], int(message_list[4]))

            tuple_ret = self.lookup_file(int(message_list[2]), file_name, curr_addr)
            curr_status = False

            if tuple_ret != (" ", 0):
                curr_status = True

            else:
                curr_status = False

            if curr_status:
                a_1 = str(tuple_ret[0])
                a_2 = str(tuple_ret[1])

                message = "target_file_spot" + " "+ a_1 + " " + a_2
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                soc.connect(curr_addr)
                soc.send(message.encode('utf-8'))
                soc.close()

        if message_list[0] == "target_file_spot":
            ans1 = message_list[1]
            ans2 = int(message_list[2])
            self.file_curr_node = (ans1, ans2)
            self.file_bool = True
            client.close()

        if message_list[0] == "put_file":
            _folder_name = self.host+"_"+str(self.port)
            path_file = self.host+"_"+str(self.port) + "/" + message_list[1]

            file_recv = False

            num_check = 1
            while(num_check == 1):
                try:
                    self.recieveFile(client, path_file)
                    file_recv = True
                except:
                    file_recv = False
                    num_check = 0
                    pass

            mess = ""
            if file_recv:
                mess = "no_error_file"
            else:
                mess = "error_file"

            self.files.append(message_list[1])
            # store file in system
            client.close()
            x_x = message_list[1]
            msg = "put_backup" + " " + x_x + " " + mess
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.connect(self.predecessor)
            soc.send(msg.encode('utf-8'))
            soc.close()

        ############################################################################# get func file
        if message_list[0] == "get_lookup_file":
            client.close()
            key_of_new_file = int(message_list[2])
            file_name = message_list[1]
            curr_addr = (message_list[3], int(message_list[4]))
            tuple_ret = self.get_file_lookup(key_of_new_file, file_name, curr_addr)

            curr_status = False
            if tuple_ret != (" ", 0):
                curr_status = True
            else:
               curr_status = False

            if curr_status:
                msg_type = "getfunc_file_spot" 
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ans1 = str(tuple_ret[0])
                ans2 = str(tuple_ret[1])
                conn.connect(curr_addr)
                message = msg_type + " "+ ans1 + " " + ans2
                conn.send(message.encode('utf-8'))
                conn.close()

        if message_list[0] == "getfunc_file_spot":
            self.getfunc_file = (message_list[1], int(message_list[2]))
            client.close()

        if message_list[0] == "send_file":
            file = message_list[1]

            if file in self.files:
                message = "file_found"
                client.send(message.encode('utf-8'))

            else:
                message = "file_not_found"
                client.send(message.encode('utf-8'))

            client.close()

        ################################################### file rehashing

        # here we send the rehashed and del from own directory
        if message_list[0] == "succ_send_files_in_range":
            file_str = ""
            new_key = int(message_list[1])

            for file in self.files:
                file_id = int(self.hasher(file))

                ans = self.range_checker(file_id, new_key, self.key)
                if ans:
                    file_str = file_str + " " + file + " "

            file_str = file_str.strip()

            client.send(file_str.encode('utf-8'))
            client.close()

        if message_list[0] == "files_to_del":
            files_to_del = message_list[1:]

            for file in self.files:
                if file in files_to_del:
                    self.files.remove(file)

            client.close()

        # asking succ for files to add in backup
        if message_list[0] == "succ_send_files":
            file_str = ""
            file_came = False

            if len(message_list) > 0:
                file_came = True
            else:
                file_came = False

            for file in self.files:
                file_str = file_str + " " + file + " "

            _msg = ""
            if file_came:
                _msg = "file_added"

            file_str = file_str.strip()
            client.send(file_str.encode('utf-8'))
            client.close()

        if message_list[0] == "file_key_is_xx":
            _key = self.hasher(message_list[0])
            client.close()


        # asking pred to store succs backup files
        if message_list[0] == "store_backup_files":
            file_list = message_list[1:]
            for file in file_list:
                self.backUpFiles.append(file)
            client.close()

        ####################################################### leave
        if message_list[0] == "leaving":
            client.close()
            pre1 = message_list[1]
            pre2 = int(message_list[2])
            self.predecessor = (pre1, pre2)
            hos = str(self.host)
            por = str(self.port)
            su1 = str(self.successor[0])
            su2 = str(self.successor[1])

            message = "going_change_successor" + " " + hos + " " + por + " " + su1 + " " + su2
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            p_1 = self.predecessor[0]
            p_2 = self.predecessor[1]
            soc.connect((p_1, p_2))
            soc.send(message.encode('utf-8'))
            soc.close()

        if message_list[0] == "going_change_succ_succ":
            self.leave_bool = True
            s_1 = message_list[1]
            s_2 = int(message_list[2])
            self.succ_succ =  (s_1, s_2)
            client.close()
            self.leave_bool= False

        if message_list[0] == "going_change_successor":
            client.close()
            suc1 = message_list[1]
            suc2 = int(message_list[2])
            self.successor = (suc1, suc2)

            suc_suc1 = message_list[3]
            suc_suc2 = int(message_list[4])

            self.succ_succ =  (suc_suc1, suc_suc2)

            s_1 = str(self.successor[0])
            s_2 = str(self.successor[1])

            message = "going_change_succ_succ" + " " + s_1 + " " + s_2
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.connect(self.predecessor)
            soc.send(message.encode('utf-8'))
            soc.close()

        if message_list[0] == "leaving_succ_take_files":
            file_list = message_list[1:]
            for file in file_list:
                self.files.append(file)

            client.close()
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_socket.connect(self.predecessor)

            message = "store_backup_files"
            for file in self.files:
                message = message + " " + file + " "

            message = message.strip()
            new_socket.send(message.encode('utf-8'))
            new_socket.close()


        ######################################################## file rehashing part 2



    def listener(self):
        '''xx'''
        listener = socket.socket()
        listener.bind((self.host, self.port))
        listener.listen(10)
        while not self.stop:
            client, addr = listener.accept()
            threading.Thread(target = self.handleConnection, args = (client, addr)).start()
        print ("Shutting down node:", self.host, self.port)
        try:
            listener.shutdown(2)
            listener.close()
        except:
            listener.close()




    def pinging(self):
        '''vvv'''
        node_alive = True
        num_tracer = False
        succ_msg = ""

        while 1:

            if self.leave_bool:
                node_alive = False

            elif not self.leave_bool:
                h_o = str(self.host)
                p_o = str(self.port)
                message = "alive_ping" + " "+ h_o + " " + p_o + " " + "yes"

                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    succ_msg = ""
                    s_1 = self.successor[0]
                    s_2 = self.successor[1]
                    soc.connect((s_1, s_2))
                    soc.send(message.encode('utf-8'))
                    message = soc.recv(1024).decode('utf-8')
                    succ_msg = message
                    soc.close()

                    if succ_msg != "":
                        node_alive = True

                except:
                    succ_msg = ""
                    node_alive = False
                    self.num_pings = self.num_pings + 1
                 

                if self.num_pings == 2:
                    num_tracer = True
                else:
                    num_tracer = False

                if num_tracer:

                    node_alive = True
                    self.successor = self.succ_succ
                    self.num_pings = 0


                    h_o = str(self.host)
                    p_o = str(self.port)

                    message = "dead_ping" + " " + h_o + " "+ p_o + " " + "no"
                    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    conn.connect(self.successor)
                    conn.send(message.encode('utf-8'))
                    conn.close()

                    if node_alive:
                        message_join = "succ_changed"
                    else:
                        message_join = "succ_not_changed"

                    # update your predecessor's consecutive successor
                    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    soc.connect(self.predecessor)
                    suc1 = str(self.successor[0])
                    suc2 = str(self.successor[1])

                    message = "suc_suc_change_ping" + " " + suc1 + " " + suc2 + " " + message_join
                    soc.send(message.encode('utf-8'))
                    soc.close()

                    new_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    new_conn.connect(self.successor)
                    file_list = "leaving_succ_take_files"

                    for file in self.backUpFiles:
                        file_list = file_list + " " + file + " "

                    file_list = file_list.strip()

                    new_conn.send(file_list.encode('utf-8'))
                    new_conn.close()
                time.sleep(0.5)



    def thread_ping(self):
        '''hhh'''
        threading.Thread(target = self.pinging).start()


    def lookup(self,key, new_node_address):
        '''hh'''
        tuple_ret = (" ", 0)
        # ask your successor for its key

        successor_key = self.hasher(self.successor[0] + str(self.successor[1]))

        if successor_key > self.key:
            # successor > node's key > self.key
            if successor_key>key and key >=self.key: # self.key<=key<successor_key

                return self.successor

            else:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                message_code= "lookup"
                n_0 = str(new_node_address[0])
                n_1 = str(new_node_address[1])
                
                message = message_code + " " + n_0 + " " + n_1 +" " +  str(key)
                soc.connect(self.successor)
                soc.send(message.encode('utf-8'))
                soc.close()

        else: # this is the wrap around case
            x_x = (key<=successor_key)
            if x_x or (key>self.key): # correct range found
                return self.successor

            else:
                message_code = "lookup"
                n_0 = str(new_node_address[0])
                n_1 = str(new_node_address[1])
                message = message_code + " " + n_0 + " " + n_1 +" " +  str(key)
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                soc.connect(self.successor)
                soc.send(message.encode('utf-8'))
                soc.close()

        return tuple_ret


    def range_checker(self, file_key, new_node_key, old_key):
        '''
        if ((new_node_key >= file_key) and (file_key > old_key)):
            move = True'''
        move = False
        if file_key == new_node_key:
            move = True

        if ((old_key > file_key) and (new_node_key> file_key)):
            move = True

        return move

    def file_saver(self, file_name):
        '''bb'''
        pass


    def join(self, joiningAddr):
        '''cc'''
        # if empty string, then just set pred and successor to ur own host and port
        if joiningAddr == "":
            self.successor = (self.host,self.port)
            self.predecessor = (self.host,self.port)

        else:
            curr_key = self.key

            j_1 = joiningAddr[0]
            j_2 = joiningAddr[1]

            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            message = "lookup" + " " + str(self.host) + " " + str(self.port) +" "+ str(curr_key)
            soc.connect((j_1,j_2))
            soc.send(message.encode('utf-8'))
            soc.close()

            control = False

            length_file_node = len(self.position)

            if  length_file_node == 0:
                control = True
            else:
                control = False

            while control:
                length_file_node = len(self.position)

                if  length_file_node == 0:
                    control = True
                else:
                    control = False


            self.successor = self.position

            if not self.join_bool:
                
              
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                msg_type = "join_change_pred"
                hos = str(self.host) 
                por = str(self.port)
                conn.connect(self.successor)
                message = msg_type + " " + hos + " " + por
                conn.send(message.encode('utf-8'))

                self.join_one_node = False
                self.joinedx = True

                message = conn.recv(1024).decode('utf-8')
                message_list = message.split()
                conn.close()
                self.succ_succ = (message_list[1], int(message_list[2]))

            elif self.join_bool:

                self.predecessor = self.successor
                msg_type = "sec_node_pred"
                hos = str(self.host) 
                por = str(self.port)

                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                message = msg_type + " " + hos  + " " + por
                if not self.joinedx:
                    self.join_one_node = True

                conn.connect(self.successor)
                conn.send(message.encode('utf-8'))
                self.succ_succ = (self.host, int(self.port))
                conn.close()


        # call ping thread

        self.thread_ping()

        # threading.Thread(target = self.check, args = ()).start()

        #### FILE REHASHING ####
        # send msg to succ

        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.connect(self.successor)
        hos = self.host
        por = str(self.port)
        k_k = str(self.key) 
        message = "succ_send_files_in_range" + " " + k_k + " " + hos + " " + por
        file_socket.send(message.encode('utf-8'))
        message = file_socket.recv(1024).decode('utf-8')
        file_str = message
        file_list = message.split()

        for file in file_list:
            self.files.append(file)

        file_socket.close()

        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.connect(self.successor)
        message = "files_to_del" + " " + file_str
        file_socket.send(message.encode('utf-8'))
        message = file_socket.recv(1024).decode('utf-8')
        file_socket.close()

        # ask succ to send its update file list and store it in backup
        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.connect(self.successor)
        message = "succ_send_files"
        file_socket.send(message.encode('utf-8'))
        time.sleep(0.01)
        message = file_socket.recv(1024).decode('utf-8')
        file_list = message.split()
        for file in file_list:
            self.backUpFiles.append(file)

        file_socket.close()

        _file_sent = False
        address_to_send = self.predecessor
        # send ur updated files to prdecessor to store in its backup
        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.connect(self.predecessor)
        message = "store_backup_files"

        if address_to_send != ():
            _file_sent= True

        file_list = message.split()
        for file in self.files:
            message = message + " " + file + " "
            _file_sent = True

        _file_sent = False
        message.strip()
        file_socket.send(message.encode('utf-8'))
        file_socket.close()




    def lookup_file(self, key, File_name, curr_addr):
        '''nn'''
        tuple_ret = (" ", 0)
        # ask your successor for its key

        successor_key = self.hasher(self.successor[0] + str(self.successor[1]))

        if self.key == key:
            return curr_addr

        if successor_key > self.key:
            # successor > node's key > self.key
            if successor_key>key and key >self.key: # self.key<=key<successor_key

                return self.successor

            else:
                lookup_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                lookup_socket.connect(self.successor)
                message_code = "lookup_file"
                message = message_code + " " + File_name +" " +  str(key) + " " + curr_addr[0] + " " + str(curr_addr[1])
                lookup_socket.send(message.encode('utf-8'))
                lookup_socket.close()

        else: # this is the wrap around case
            x_x = (key<successor_key)
            if x_x or (key>self.key): # correct range found
                return self.successor

            else:
                lookup_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                lookup_socket.connect(self.successor)
                message_code = "lookup_file"
                message = message_code + " " + File_name +" " +  str(key) + " " + curr_addr[0] + " " + str(curr_addr[1])
                lookup_socket.send(message.encode('utf-8'))
                lookup_socket.close()

        return tuple_ret

    def put(self, fileName):
        '''hh'''
        file_node = ()
        curr_addr = (self.host, self.port)
        file_id = int(self.hasher(fileName))

        file_node_lookup = self.lookup_file(file_id, fileName, curr_addr)

        if file_node_lookup == (" ", 0):
            # will send file to file node
            control = False

            length_file_node = len(self.file_curr_node)

            if  length_file_node == 0:
                control = True
            else:
                control = False

            while control:
                length_file_node = len(self.file_curr_node)

                if  length_file_node == 0:
                    control = True
                else:
                    control = False

            file_node = self.file_curr_node
            self.file_curr_node = ()
        else:
            file_node = file_node_lookup

        # send file
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.connect(file_node)
        message = "put_file" + " " + fileName
        new_socket.send(message.encode('utf-8'))
        _path_file = self.host+"_"+str(self.port) + "/" + fileName
        time.sleep(0.5)
        self.sendFile(new_socket, fileName)
        new_socket.close()


    def get_file_lookup(self, key, File_name, curr_addr):
        '''vv'''
        tuple_ret = (" ", 0)
        # ask your successor for its key

        successor_key = self.hasher(self.successor[0] + str(self.successor[1]))

        if self.key == key:
            return curr_addr

        if successor_key > self.key:
            # successor > node's key > self.key
            if successor_key>key and key >self.key: # self.key<=key<successor_key

                return self.successor

            else:
                lookup_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                lookup_socket.connect(self.successor)
                message_code = "get_lookup_file"
                message = message_code + " " + File_name +" " +  str(key) + " " + curr_addr[0] + " " + str(curr_addr[1])
                lookup_socket.send(message.encode('utf-8'))
                lookup_socket.close()

        else: # this is the wrap around case
            x = (key<successor_key)
            if x or (key>self.key): # correct range found
                return self.successor

            else:
                lookup_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                lookup_socket.connect(self.successor)
                message_code = "get_lookup_file"
                message = message_code + " " + File_name +" " +  str(key) + " " + curr_addr[0] + " " + str(curr_addr[1])
                lookup_socket.send(message.encode('utf-8'))
                lookup_socket.close()

        return tuple_ret


    def get(self, fileName):
        '''gg'''
        file_node = ()
        curr_addr = (self.host, self.port)
        file_id = int(self.hasher(fileName))

        file_node_lookup = self.get_file_lookup(file_id, fileName, curr_addr)

        if file_node_lookup == (" ", 0):
            # will send file to file node
            control = False

            length_file_node = len(self.getfunc_file)

            if  length_file_node == 0:
                control = True
            else:
                control = False

            while control:
                length_file_node = len(self.getfunc_file)

                if  length_file_node == 0:
                    control = True
                else:
                    control = False

            file_node = self.getfunc_file
            self.getfunc_file = ()
        else:
            file_node = file_node_lookup

        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.connect(file_node)
        message = "send_file" + " " + fileName + " " + self.host + " " + str(self.port)
        new_socket.send(message.encode('utf-8'))

        msg = new_socket.recv(1024).decode('utf-8')

        msg_list = msg.split()

        _path_file = self.host+"_"+str(self.port) + "/" + fileName


        if msg_list[0] == "file_found":
            new_socket.close()
            self.files.append(fileName)
            return fileName

        elif msg_list[0] == "file_not_found":
            new_socket.close()
            return None


    def leave(self):
        '''bb'''
        self.leave_bool = True


        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.connect(self.successor)

        pred1 = str(self.predecessor[0]) 
        pred2 = str(self.predecessor[1])
        msg_code = "leaving" 

        message = msg_code + " " + pred1 + " " + pred2
        soc.send(message.encode('utf-8'))
        soc.close()

        # send files to successor
        #EMAAN PLZZ UPDATE BACKUP FILESSSSS

        new_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_conn.connect(self.successor)
        file_list = "leaving_succ_take_files"

        for file in self.files:
            file_list = file_list + " " + file + " "

        file_list = file_list.strip()

        new_conn.send(file_list.encode('utf-8'))
        new_conn.close()


        self.kill()


    def sendFile(self, soc, fileName):
        '''vv'''
        fileSize = os.path.getsize(fileName)
        soc.send(str(fileSize).encode('utf-8'))
        soc.recv(1024).decode('utf-8')
        with open(fileName, "rb") as file:
            contentChunk = file.read(1024)
            while contentChunk!="".encode('utf-8'):
                soc.send(contentChunk)
                contentChunk = file.read(1024)

    def recieveFile(self, soc, fileName):
        '''ggg'''
        fileSize = int(soc.recv(1024).decode('utf-8'))
        soc.send("ok".encode('utf-8'))
        contentRecieved = 0
        file = open(fileName, "wb")
        while contentRecieved < fileSize:
            contentChunk = soc.recv(1024)
            contentRecieved += len(contentChunk)
            file.write(contentChunk)
        file.close()

    def kill(self):
        '''vv'''
        # DO NOT EDIT THIS, used for code testing
        self.stop = True
