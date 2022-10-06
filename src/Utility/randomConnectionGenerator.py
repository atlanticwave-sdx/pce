import numpy as np
import json

class RandomConnectionGenerator:
    def __init__(self, N):
        """
        init
        @param N number of nodes of the topology 
        """
        self.num_nodes = N

    def randomConnectionGenerator(self, querynum, l_bw, u_bw, l_lat, u_lat, seed = 2022):
        """
        Create a random TM
        @param querynum number of connections 
        @return a list of connections, each of which is a list [src, des, bw, lat]
        """
        np.random.seed(seed)
        connection = []
        bw = self.lognormal((l_bw+u_bw)/2.0, 1, querynum)
        if querynum <= self.num_nodes:
            for i in range(querynum):
                query = []
                query.append(np.random.randint(1,(self.num_nodes+1)/2.0))
                query.append(np.random.randint((self.num_nodes+1)/2.0, self.num_nodes))
                #query.append(np.random.randint(l_bw, u_bw))
                query.append(bw[i])
                query.append(np.random.randint(l_lat, u_lat))
                connection.append(query)
        else:
            for i in range(querynum):
                query = []
                src=np.random.randint(0,self.num_nodes)
                query.append(src)
                dest=np.random.randint(0,self.num_nodes)
                while (dest ==src):
                    dest=np.random.randint(0,self.num_nodes)
                query.append(dest)
                #query.append(np.random.randint(l_bw, u_bw))
                query.append(bw[i])
                query.append(np.random.randint(l_lat, u_lat))
                connection.append(query)

        with open('connection.json', 'w') as json_file:
            data = connection
            json.dump(data, json_file, indent=4)
        
        return connection

    def lognormal(self, mu, sigma, size):
        normal_std = np.sqrt(np.log(1 + (sigma/mu)**2))
        normal_mean = np.log(mu) - normal_std**2 / 2
        return np.random.lognormal(normal_mean, normal_std, size)

    def random(self, min, mx, size):
        return np.random.randint(min, max, 1000)

    def connectionSplitter(self, connection, group_size):
        if len(connection) > 20:
            connection.sort(key=lambda x: x[2])

        splitted_list = [connection[x:x+group_size] for x in range(0, len(connection),group_size)]

        with open('splittedconnection.json', 'w') as json_file:
            data = splitted_list
            json.dump(data, json_file, indent=4)

        print(splitted_list)


#tm = RandomConnectionGenerator(20)
#connection = tm.randomConnectionGenerator(3, 100, 1000, 1000, 1500, 2022)
#split_connection = tm.connectionSplitter(5)