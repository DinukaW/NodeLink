import socket
import threading
import os
import time
import hashlib


class Node:
    def __init__(self, host, port, bootstrap_host="localhost", bootstrap_port=9000):
        self.stop = False
        self.host = host
        self.port = port
        self.M = 16
        self.N = 2**self.M
        self.key = self.hasher(host+str(port))
        
        # Bootstrap server connection
        self.bootstrap_host = bootstrap_host
        self.bootstrap_port = bootstrap_port
        
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
        
        # Start heartbeat to bootstrap server
        self.heartbeat_thread = None
        
        # Start file discovery thread
        threading.Thread(target=self.discover_files, daemon=True).start()


    def hasher(self, key):
        '''nn'''
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.N
    
    def send_to_bootstrap(self, message):
        """Send message to bootstrap server and get response"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  # 5 second timeout
            sock.connect((self.bootstrap_host, self.bootstrap_port))
            sock.send(message.encode('utf-8'))
            response = sock.recv(1024).decode('utf-8')
            sock.close()
            return response
        except socket.timeout:
            print("Bootstrap server timeout")
            return None
        except ConnectionRefusedError:
            print("Bootstrap server not available")
            return None
        except Exception as e:
            print(f"Error communicating with bootstrap server: {e}")
            return None
    
    def send_heartbeat(self):
        """Send heartbeat to bootstrap server"""
        while not self.stop:
            try:
                message = f"heartbeat {self.host} {self.port}"
                response = self.send_to_bootstrap(message)
                if response != "ack":
                    print(f"Bootstrap server heartbeat failed: {response}")
            except Exception as e:
                print(f"Heartbeat error: {e}")
            
            # Sleep in smaller chunks to respond to stop signal faster
            for _ in range(30):  # 3 seconds total, check stop every 0.1s
                if self.stop:
                    break
                time.sleep(0.1)
    
    def discover_files(self):
        """Automatically discover files in the node's directory"""
        node_dir = f"{self.host}_{self.port}"
        
        while not self.stop:
            try:
                if os.path.exists(node_dir):
                    # Get current files in directory
                    current_files = set()
                    for file_name in os.listdir(node_dir):
                        file_path = os.path.join(node_dir, file_name)
                        if os.path.isfile(file_path) and not file_name.startswith('.'):
                            current_files.add(file_name)
                    
                    # Get files currently tracked by this node
                    tracked_files = set(self.files)
                    
                    # Find new files to add
                    new_files = current_files - tracked_files
                    for file_name in new_files:
                        print(f"Auto-discovered file: {file_name}")
                        # Check if this file should be stored on this node based on hash
                        file_id = int(self.hasher(file_name))
                        responsible_node = self.lookup_file(file_id, file_name, (self.host, self.port))
                        
                        # Wait for lookup to complete
                        timeout_count = 0
                        while responsible_node == (" ", 0) and timeout_count < 10:
                            time.sleep(0.1)
                            timeout_count += 1
                            responsible_node = self.lookup_file(file_id, file_name, (self.host, self.port))
                        
                        if responsible_node == (self.host, self.port) or responsible_node == (" ", 0):
                            # This node is responsible for the file or lookup failed
                            self.files.append(file_name)
                            print(f"File {file_name} belongs to this node")
                        else:
                            # File should be moved to the responsible node
                            print(f"File {file_name} should be stored on {responsible_node}")
                            try:
                                # Verify file exists before transfer
                                file_path = os.path.join(node_dir, file_name)
                                if os.path.exists(file_path):
                                    # Send file to responsible node
                                    self.transfer_file_to_node(file_name, responsible_node)
                                    # Remove from local directory after successful transfer
                                    os.remove(file_path)
                                    print(f"Transferred {file_name} to {responsible_node}")
                                else:
                                    print(f"File {file_name} does not exist for transfer")
                            except Exception as e:
                                print(f"Failed to transfer {file_name}: {e}")
                                # Keep the file locally if transfer fails
                                if file_name not in self.files:
                                    self.files.append(file_name)
                    
                    # Find files that were removed
                    removed_files = tracked_files - current_files
                    for file_name in removed_files:
                        if file_name in self.files:
                            print(f"File removed: {file_name}")
                            self.files.remove(file_name)
                            
            except Exception as e:
                print(f"File discovery error: {e}")
            
            # Check every 5 seconds
            for _ in range(50):  # 5 seconds total, check stop every 0.1s
                if self.stop:
                    break
                time.sleep(0.1)
    
    def transfer_file_to_node(self, file_name, target_node):
        """Transfer a file to the responsible node"""
        try:
            # Validate target node
            if not target_node or len(target_node) != 2 or target_node == (" ", 0):
                raise Exception(f"Invalid target node: {target_node}")
            
            # Check if file exists
            file_path = os.path.join(f"{self.host}_{self.port}", file_name)
            if not os.path.exists(file_path):
                raise Exception(f"File {file_path} does not exist")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)  # 10 second timeout
            sock.connect(target_node)
            
            message = f"put_file {file_name}"
            sock.send(message.encode('utf-8'))
            
            # Send the file
            time.sleep(0.5)
            self.sendFile(sock, file_path)
            sock.close()
            
        except Exception as e:
            try:
                sock.close()
            except:
                pass
            raise Exception(f"Transfer failed: {e}")

    def handleConnection(self, client, addr):
        '''nn'''
        incoming_message = client.recv(1024).decode('utf-8')
        message_list = incoming_message.split()

        if message_list[0] =="lookup":
            client.close()
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
            
        if message_list[0] == "change_succ_1":
            succ1 = str(message_list[1])
            succ2 = int(message_list[2])
            self.successor = (succ1, succ2)
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

            # Check if file is in main files
            if file in self.files:
                message = "file_found"
                client.send(message.encode('utf-8'))
            # Also check if file is in backup files (in case main node left)
            elif file in self.backUpFiles:
                message = "file_found"
                client.send(message.encode('utf-8'))
                # Move from backup to main files since it's being accessed
                self.backUpFiles.remove(file)
                self.files.append(file)
                print(f"Retrieved file from backup: {file}")
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

        # Handle backup file restoration when a node leaves
        if message_list[0] == "restore_backup_file":
            backup_file = message_list[1]
            if backup_file in self.backUpFiles:
                # Move from backup to main files
                self.backUpFiles.remove(backup_file)
                if backup_file not in self.files:
                    self.files.append(backup_file)
                    print(f"Restored backup file: {backup_file}")
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

            if len(message_list) >= 5:
                suc_suc1 = message_list[3]
                suc_suc2 = int(message_list[4])
                self.succ_succ = (suc_suc1, suc_suc2)

                s_1 = str(self.successor[0])
                s_2 = str(self.successor[1])

                message = "going_change_succ_succ" + " " + s_1 + " " + s_2
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    soc.connect(self.predecessor)
                    soc.send(message.encode('utf-8'))
                    soc.close()
                except Exception as e:
                    print(f"Error notifying predecessor: {e}")

        # Handle topology updates from bootstrap server
        if message_list[0] == "topology_update_pred":
            pred_host = message_list[1]
            pred_port = int(message_list[2])
            self.predecessor = (pred_host, pred_port)
            print(f"Topology update: New predecessor {self.predecessor}")
            client.close()

        if message_list[0] == "topology_update_succ":
            succ_host = message_list[1]
            succ_port = int(message_list[2])
            self.successor = (succ_host, succ_port)
            print(f"Topology update: New successor {self.successor}")
            client.close()

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
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        listener.listen(10)
        listener.settimeout(1.0)  # Add timeout to allow checking stop condition
        
        while not self.stop:
            try:
                client, addr = listener.accept()
                threading.Thread(target = self.handleConnection, args = (client, addr), daemon=True).start()
            except socket.timeout:
                continue  # Check stop condition
            except Exception as e:
                if not self.stop:
                    print(f"Listener error: {e}")
                break
                
        print ("Shutting down node:", self.host, self.port)
        try:
            listener.shutdown(socket.SHUT_RDWR)
            listener.close()
        except:
            listener.close()




    def pinging(self):
        '''vvv'''
        node_alive = True
        num_tracer = False
        succ_msg = ""

        while not self.stop:

            if self.leave_bool:
                node_alive = False
                break  # Exit the loop when leaving

            elif not self.leave_bool:
                h_o = str(self.host)
                p_o = str(self.port)
                message = "alive_ping" + " "+ h_o + " " + p_o + " " + "yes"

                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    succ_msg = ""
                    # Check if successor is valid before using it
                    if (self.successor and len(self.successor) == 2 and 
                        self.successor != (self.host, self.port) and
                        isinstance(self.successor[0], str) and 
                        isinstance(self.successor[1], int)):
                        
                        s_1 = self.successor[0]
                        s_2 = self.successor[1]
                        soc.settimeout(3.0)  # Set timeout
                        soc.connect((s_1, s_2))
                        soc.send(message.encode('utf-8'))
                        message = soc.recv(1024).decode('utf-8')
                        succ_msg = message
                        soc.close()

                        if succ_msg != "":
                            node_alive = True
                    else:
                        # If no valid successor, skip pinging
                        node_alive = True
                        
                except (socket.timeout, ConnectionRefusedError, OSError) as e:
                    print(f"Successor {self.successor} is not responding: {e}")
                    try:
                        soc.close()
                    except:
                        pass
                    # Try to get updated topology from bootstrap server
                    try:
                        response = self.send_to_bootstrap(f"lookup {self.host} {self.port}")
                        if response and response.startswith("successor"):
                            parts = response.split()
                            if len(parts) >= 3:
                                new_succ = (parts[1], int(parts[2]))
                                if new_succ != self.successor:
                                    print(f"Updated successor from {self.successor} to {new_succ}")
                                    self.successor = new_succ
                    except Exception as update_error:
                        print(f"Failed to update successor: {update_error}")
                        
                    node_alive = False

                if self.num_pings == 2:
                    num_tracer = True
                else:
                    num_tracer = False

                if num_tracer:

                    node_alive = True
                    self.successor = self.succ_succ
                    self.num_pings = 0

                    # Only proceed if we have a valid successor
                    if self.successor and len(self.successor) == 2:
                        h_o = str(self.host)
                        p_o = str(self.port)

                        message = "dead_ping" + " " + h_o + " "+ p_o + " " + "no"
                        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                            conn.connect(self.successor)
                            conn.send(message.encode('utf-8'))
                            conn.close()
                        except Exception as e:
                            print(f"Dead ping error: {e}")
                            conn.close()

                    if node_alive:
                        message_join = "succ_changed"
                    else:
                        message_join = "succ_not_changed"

                    # update your predecessor's consecutive successor
                    if self.predecessor and len(self.predecessor) == 2 and self.successor and len(self.successor) == 2:
                        try:
                            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            soc.connect(self.predecessor)
                            suc1 = str(self.successor[0])
                            suc2 = str(self.successor[1])

                            message = "suc_suc_change_ping" + " " + suc1 + " " + suc2 + " " + message_join
                            soc.send(message.encode('utf-8'))
                            soc.close()
                        except Exception as e:
                            print(f"Predecessor update error: {e}")

                    # Transfer backup files to successor
                    if self.successor and len(self.successor) == 2 and self.backUpFiles:
                        try:
                            new_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            new_conn.connect(self.successor)
                            file_list = "leaving_succ_take_files"

                            for file in self.backUpFiles:
                                file_list = file_list + " " + file + " "

                            file_list = file_list.strip()

                            new_conn.send(file_list.encode('utf-8'))
                            new_conn.close()
                        except Exception as e:
                            print(f"File transfer error: {e}")
                    
            # Sleep in smaller chunks to respond to stop signal faster
            for _ in range(5):  # 0.5 seconds total, check stop every 0.1s
                if self.stop:
                    break
                time.sleep(0.1)



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
        # Register with bootstrap server
        try:
            message = f"register {self.host} {self.port}"
            response = self.send_to_bootstrap(message)
            
            if not response:
                print("Failed to connect to bootstrap server")
                return False
                
            response_parts = response.split()
            
            if response_parts[0] == "first_node":
                # This is the first node in the network
                self.successor = (self.host, self.port)
                self.predecessor = (self.host, self.port)
                print(f"Joined as first node with key {self.key}")
                
            elif response_parts[0] == "join_position":
                # Join existing network
                successor_host = response_parts[1]
                successor_port = int(response_parts[2])
                predecessor_host = response_parts[3]
                predecessor_port = int(response_parts[4])
                
                self.successor = (successor_host, successor_port)
                self.predecessor = (predecessor_host, predecessor_port)
                
                # Notify successor and predecessor
                self.notify_successor_predecessor()
                print(f"Joined network with key {self.key}, successor: {self.successor}, predecessor: {self.predecessor}")
                
            else:
                print(f"Bootstrap server error: {response}")
                return False
                
        except Exception as e:
            print(f"Error joining network: {e}")
            return False
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        self.heartbeat_thread.start()
        
        # Call ping thread for node-to-node monitoring
        self.thread_ping()

        # File rehashing logic remains the same
        self.perform_file_rehashing()
        
        return True
    
    def notify_successor_predecessor(self):
        """Notify successor and predecessor about the new node"""
        try:
            # Notify successor to update its predecessor
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            message = f"change_pred_1 {self.host} {self.port}"
            soc.connect(self.successor)
            soc.send(message.encode('utf-8'))
            soc.close()
            
            # Notify predecessor to update its successor
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            message = f"change_succ_1 {self.host} {self.port}"
            soc.connect(self.predecessor)
            soc.send(message.encode('utf-8'))
            soc.close()
            
        except Exception as e:
            print(f"Error notifying neighbors: {e}")
    
    def perform_file_rehashing(self):
        """Perform file rehashing after joining"""
        try:
            # File rehashing logic - same as original but in separate method
            if self.successor != (self.host, self.port):  # Only if not the only node
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

                # send ur updated files to predecessor to store in its backup
                if self.predecessor != (self.host, self.port):
                    file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    file_socket.connect(self.predecessor)
                    message = "store_backup_files"

                    for file in self.files:
                        message = message + " " + file + " "

                    message = message.strip()
                    file_socket.send(message.encode('utf-8'))
                    file_socket.close()
                    
        except Exception as e:
            print(f"Error in file rehashing: {e}")




    def lookup_file(self, key, File_name, curr_addr):
        '''nn'''
        # Check if this node is responsible for the key
        successor_key = self.hasher(self.successor[0] + str(self.successor[1]))

        if self.key == key:
            return curr_addr

        # If we're the only node, we're responsible
        if self.successor == (self.host, self.port):
            return curr_addr

        if successor_key > self.key:
            # Normal case: successor > self.key
            if key > self.key and key <= successor_key:
                return self.successor
            elif key <= self.key:
                return curr_addr  # This node is responsible
            else:
                # Forward to successor - but we don't wait for response in discovery
                # Return the successor as best guess
                return self.successor

        else: # Wrap around case: successor < self.key
            if key > self.key or key <= successor_key:
                return self.successor
            else:
                return curr_addr  # This node is responsible

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
        
        # Use full path for the file
        file_path = self.host+"_"+str(self.port) + "/" + fileName
        time.sleep(0.5)
        self.sendFile(new_socket, file_path)
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

        # Validate file_node before connecting
        if not file_node or len(file_node) != 2:
            print(f"Invalid file node: {file_node}")
            return None

        try:
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
                
        except Exception as e:
            print(f"Error retrieving file: {e}")
            return None


    def transfer_files_before_leaving(self):
        """Transfer files to successor and predecessor before leaving the network"""
        if self.successor == (self.host, self.port):
            print("This is the only node in the network - no files to transfer")
            return
            
        print(f"Transferring {len(self.files)} files to successor and predecessor before leaving...")
        
        # Distribute files randomly between successor and predecessor
        import random
        
        for i, file_name in enumerate(self.files):
            try:
                file_path = os.path.join(f"{self.host}_{self.port}", file_name)
                if os.path.exists(file_path):
                    # Randomly choose successor or predecessor
                    if random.choice([True, False]) and self.predecessor != (self.host, self.port):
                        target_node = self.predecessor
                        target_name = "predecessor"
                    else:
                        target_node = self.successor
                        target_name = "successor"
                    
                    print(f"Transferring {file_name} to {target_name} {target_node}")
                    
                    # Transfer the actual file
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10.0)
                    sock.connect(target_node)
                    
                    message = f"put_file {file_name}"
                    sock.send(message.encode('utf-8'))
                    
                    time.sleep(0.2)  # Small delay
                    self.sendFile(sock, file_path)
                    sock.close()
                    
                    print(f"Successfully transferred {file_name} to {target_node}")
                    
            except Exception as e:
                print(f"Failed to transfer {file_name}: {e}")
                # Continue with other files
                continue
        
        # Also send backup files to ensure they don't get lost
        if self.backUpFiles:
            print(f"Transferring {len(self.backUpFiles)} backup files to successor")
            try:
                for backup_file in self.backUpFiles:
                    # Try to send backup files to successor
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(self.successor)
                    message = f"restore_backup_file {backup_file}"
                    sock.send(message.encode('utf-8'))
                    sock.close()
            except Exception as e:
                print(f"Failed to transfer backup files: {e}")

    def leave(self):
        '''bb'''
        self.leave_bool = True

        # Notify bootstrap server
        try:
            message = f"leave {self.host} {self.port}"
            response = self.send_to_bootstrap(message)
            if response != "ack":
                print(f"Bootstrap server leave notification failed: {response}")
        except Exception as e:
            print(f"Error notifying bootstrap server about leave: {e}")

        # Transfer files before leaving
        self.transfer_files_before_leaving()

        # Original leave protocol - notify successor about topology change
        if self.successor != (self.host, self.port):  # Only if not the only node
            try:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                soc.connect(self.successor)

                pred1 = str(self.predecessor[0]) 
                pred2 = str(self.predecessor[1])
                msg_code = "leaving" 

                message = msg_code + " " + pred1 + " " + pred2
                soc.send(message.encode('utf-8'))
                soc.close()
            except Exception as e:
                print(f"Failed to notify successor: {e}")

        self.kill()

    def quit_with_transfer(self):
        '''Enhanced quit that transfers files before leaving'''
        self.leave_bool = True
        
        # Notify bootstrap server (same as leave)
        try:
            message = f"leave {self.host} {self.port}"
            response = self.send_to_bootstrap(message)
            if response != "ack":
                print(f"Bootstrap server leave notification failed: {response}")
        except Exception as e:
            print(f"Error notifying bootstrap server about quit: {e}")

        # Transfer files before quitting
        self.transfer_files_before_leaving()
        
        # Don't do the topology notification protocol for quit (faster exit)
        # Just kill the node
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
        # Give threads time to stop gracefully
        time.sleep(0.5)
