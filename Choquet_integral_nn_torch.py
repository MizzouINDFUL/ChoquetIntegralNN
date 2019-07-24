# -*- coding: utf-8 -*-
"""
Created on Tue Apr  9 14:53:46 2019

@author: mig5g
"""

import torch
import numpy as np

# Convert decimal to binary string
def sources_and_subsets_nodes(N):
    str1 = "{0:{fill}"+str(N)+"b}"
    a = []
    for i in range(1,2**N):
        a.append(str1.format(i, fill='0'))

    sourcesInNode = []
    sourcesNotInNode = []
    subset = []
    sourceList = list(range(N))
    # find subset nodes of a node
    def node_subset(node, sourcesInNodes):
        return [node - 2**(i) for i in sourcesInNodes]
    
    # convert binary encoded string to integer list
    def string_to_integer_array(s, ch):
        N = len(s) 
        return [(N - i - 1) for i, ltr in enumerate(s) if ltr == ch]
    
    for j in range(len(a)):
        # index from right to left
        idxLR = string_to_integer_array(a[j],'1')
        sourcesInNode.append(idxLR)  
        sourcesNotInNode.append(list(set(sourceList) - set(idxLR)))
        subset.append(node_subset(j,idxLR))

    return sourcesInNode, subset


def subset_to_indices(indices):
    return [i for i in indices]

class Choquet_integral(torch.nn.Module):
    
    def __init__(self, N_in, N_out):
        super(Choquet_integral,self).__init__()
        self.N_in = N_in
        self.N_out = N_out
        self.nVars = 2**self.N_in - 2
        
        # The FM is initialized with mean
        dummy = (1./self.N_in) * torch.ones((self.nVars, self.N_out), requires_grad=True)
#        self.vars = torch.nn.Parameter( torch.Tensor(self.nVars,N_out))
        self.vars = torch.nn.Parameter(dummy)
        
        # following function uses numpy vs pytorch
        self.sourcesInNode, self.subset = sources_and_subsets_nodes(self.N_in)
        
        self.sourcesInNode = [torch.tensor(x) for x in self.sourcesInNode]
        self.subset = [torch.tensor(x) for x in self.subset]
        
    def forward(self,inputs):    
        self.FM = self.chi_nn_vars(self.vars)
        sortInputs, sortInd = torch.sort(inputs,1, True)
        M, N = inputs.size()
        sortInputs = torch.cat((sortInputs, torch.zeros(M,1)), 1)
        sortInputs = sortInputs[:,:-1] -  sortInputs[:,1:]
        
        out = torch.cumsum(torch.pow(2,sortInd),1) - torch.ones(1, dtype=torch.int64)
        
        data = torch.zeros((M,self.nVars+1))
        
        for i in range(M):
            data[i,out[i,:]] = sortInputs[i,:] 
        
        
        ChI = torch.matmul(data,self.FM)
            
        return ChI
    
    # Converts NN-vars to FM vars
    def chi_nn_vars(self, chi_vars):
#        nVars,_ = chi_vars.size()
        chi_vars = torch.abs(chi_vars)
        #        nInputs = inputs.get_shape().as_list()[1]
        
        FM = chi_vars[None, 0,:]
        for i in range(1,self.nVars):
            indices = subset_to_indices(self.subset[i])
            if (len(indices) == 1):
                FM = torch.cat((FM,chi_vars[None,i,:]),0)
            else:
                #         ss=tf.gather_nd(variables, [[1],[2]])
                maxVal,_ = torch.max(FM[indices,:],0)
                temp = torch.add(maxVal,chi_vars[i,:])
                FM = torch.cat((FM,temp[None,:]),0)
              
        FM = torch.cat([FM, torch.ones((1,self.N_out))],0)
        FM = torch.min(FM, torch.ones(1))  
        
        return FM
    
    
if __name__=="__main__":
    
    # training samples size
    M = 700
    X_train = np.random.rand(M,N_in)*2-1
    
    N_in = 3
    N_out = 2     
            
    OWA = np.array([[0.7, 0.2, 0.1], # this is soft-max
                    [0.1,0.2,0.7]])  # soft-min
    
    # Herein we follow binary encoding instead of lexicographic encoding to represetn a FM. 
    # As for example, an FM for three inputs using binary encoding is, g = {g_1, g_2, g_{12}, g_3, g_{13}, g_{23}, g_{123}.
    
    #OWA[:] = OWA[::-1]
    #label_train = np.matmul(np.sort(X_train), OWA.T)
    label_train = np.matmul(np.sort(X_train), np.fliplr(OWA).T)
    
    # build a Choquet integral neuron with N_in inputs and N_out outputs
    net = Choquet_integral(N_in,N_out)
    
    # set the optimization algorithms and paramters the learning
    learning_rate = 0.3;
    
    # Construct our loss function and an Optimizer. The call to model.parameters()
    # in the SGD constructor will contain the learnable parameters of the two
    # nn.Linear modules which are members of the model.
    criterion = torch.nn.MSELoss(reduction='mean')
    optimizer = torch.optim.SGD(net.parameters(), lr=learning_rate)   
    
    num_epochs = 300;
    
    X_train = torch.tensor(X_train,dtype=torch.float)
    
    label_train = torch.tensor(label_train,dtype=torch.float)
    
    for t in range(num_epochs):
        # Forward pass: Compute predicted y by passing x to the model
        y_pred = net(X_train)
    
        # Compute and print loss
        loss = criterion(y_pred, label_train)
    #    print(t, loss.item())
    
        # Zero gradients, perform a backward pass, and update the weights.
        optimizer.zero_grad()
    #    net.FM.backward(retain_graph=True)
    #    print(net.FM.grad)
        loss.backward()
        optimizer.step()  
        
    
    FM = (net.chi_nn_vars(net.vars).cpu()).detach().numpy()
    print("learned FM1:\n", FM[:,0])
    print("learned FM2:\n",FM[:,1])

        

