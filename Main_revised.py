#import matplotlib.pyplot as plt
import argparse # For argument parsing
#import os.path
from conf import *  # it saves the address of data stored and where to save the data produced by algorithms
import time
import re           # regular expression library
from random import random, choice, shuffle   # for random strategy
from operator import itemgetter
import datetime
import numpy as np  
from scipy.sparse import csgraph
from scipy.spatial import distance
#from YahooExp_util_functions import getClusters, getIDAssignment, parseLine, save_to_file, initializeW, vectorize, matrixize, articleAccess
from LastFM_util_functions_2 import *#getFeatureVector, initializeW, initializeGW, parseLine, save_to_file, initializeW_clustering, initializeGW_clustering
#from LastFM_util_functions import getFeatureVector, initializeW, initializeGW, parseLine, save_to_file

from CoLin import CoLinAlgorithm
from LinUCB import LinUCBUserStruct, N_LinUCBAlgorithm
from GOBLin import GOBLinAlgorithm
from CLUB import CLUBAlgorithm
from COFIBA import COFIBAAlgorithm

from factorLinUCB import FactorLinUCBAlgorithm
from CF_UCB import CFUCBAlgorithm
from CFEgreedy import CFEgreedyAlgorithm
from EgreedyContextual import EgreedyContextualStruct
from PTS import PTSAlgorithm
from UCBPMF import UCBPMFAlgorithm

from W_Alg import LearnWAlgorithm
from W_Alg_Gradient import LearnWAlgorithm_G
from W_Alg_L1_G import LearnWAlgorithm_l1_G
from W_Alg_L1 import LearnWAlgorithm_l1
from W_Alg_Gradient_UpdateA import LearnWAlgorithm_G_UpdateA, LearnWAlgorithm_G_WRegu_UpdateA
from W_Alg_L1_G_UpdateA import LearnWAlgorithm_l1_G_UpdateA
# Command: python Main_revised.py --clusterfile Dataset/hetrec2011-delicious-2k/user_relation_adjacency_list.dat.part.200 --alg LearnWl1_UpdateA --diagnol Opt --dataset Delicious


class Article():    
    def __init__(self, aid, FV=None):
        self.id = aid
        self.featureVector = FV
        self.contextFeatureVector = FV
# structure to save data from random strategy as mentioned in LiHongs paper
class randomStruct:
    def __init__(self):
        self.reward = 0
    
def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return open(arg, 'r')  # return an open file handle

if __name__ == '__main__':
    # regularly print stuff to see if everything is going alright.
    # this function is inside main so that it shares variables with main and I dont wanna have large number of function arguments
    def printWrite():
        #print totalObservations
        recordedStats = [articles_random.reward]
        for alg_name, alg in algorithms.items():
            recordedStats.append(AlgPicked[alg_name][-1])
            recordedStats.append(alg.reward)
        #print s         
        # write to file
        save_to_file(fileNameWrite, recordedStats, tim) 


    timeRun = datetime.datetime.now().strftime('_%m_%d_%H_%M_%S')  # the current data time
    
    # Introduce argparse for future argument parsing.
    parser = argparse.ArgumentParser(description='')

    # If exsiting cluster label data.
    parser.add_argument('--clusterfile', dest="clusterfile", help="input an clustering label file", 
                        metavar="FILE", type=lambda x: is_valid_file(parser, x))
    # Select algorithm.
    parser.add_argument('--alg', dest='alg', help='Select a specific algorithm, could be CoLinUCB, GOBLin, LinUCB, M_LinUCB, Uniform_LinUCB, PTS, or ALL. No alg argument means Random.')
   
    # Designate relation matrix diagnol.
    parser.add_argument('--diagnol', dest='diagnol', required=True, help='Designate relation matrix diagnol, could be 0, 1, or Origin.') 
    # Whether show heatmap of relation matrix.
    parser.add_argument('--showheatmap', action='store_true',
                        help='Show heatmap of relation matrix.') 
    # Dataset.
    parser.add_argument('--dataset', required=True, choices=['LastFM', 'Delicious'],
                        help='Select Dataset to run, could be LastFM or Delicious.')

    # Load previous running status. Haven't finished.
    parser.add_argument('--load', 
                        help='Load previous running status. Such as Delicious_200_shuffled_Clustering_GOBLin_Diagnol_Opt__09_30_15_23_17 .')

    #Stop at certain line number. Haven't finished.
    parser.add_argument('--line', type=int,
                        help='Stop at certain line number, debug use.')

    # Designate event file, default is processed_events_shuffled.dat
    parser.add_argument('--event', 
                        help='Designate event file. Default is processed_events_shuffled.dat')  

    parser.add_argument('--particle_num', 
                        help='Particle number for PTS.')
    parser.add_argument('--dimension', 
                        help='Feature dimension used for estimation.')

    args = parser.parse_args()
    
    batchSize = 1                          # size of one batch
    
    context_dimension = 25           # context dimension
    latent_dimension = 5 #latent dimension
    alpha = 0.3     # control how much to explore
    alpha_2 = 0.5   # For CLUB
    #lambda_ = 0.2   # regularization used in matrix A
    lambda_ = 0.5   # regularization used in matrix A
    Gepsilon = 0.3   # Parameter in initializing GW
    
    UpdateWin = 1000
    totalObservations = 0

 
    OriginaluserNum = 2100
    nClusters = 100
    userNum = nClusters   
    if args.dataset == 'LastFM':
        relationFileName = LastFM_relationFileName
        address = LastFM_address
        save_address = LastFM_save_address
        FeatureVectorsFileName = LastFM_FeatureVectorsFileName
        itemNum = 19000
    else:
        relationFileName = Delicious_relationFileName
        address = Delicious_address
        save_address = Delicious_save_address
        FeatureVectorsFileName = Delicious_FeatureVectorsFileName  
        itemNum = 190000   

    if args.clusterfile:           
        label = read_cluster_label(args.clusterfile)
        userNum = nClusters = int(args.clusterfile.name.split('.')[-1]) # Get cluster number.
        W = initializeW_label(userNum, relationFileName, label, args.diagnol, args.showheatmap)   # Generate user relation matrix
        GW = initializeGW_label(Gepsilon,userNum, relationFileName, label, args.diagnol)            
    else:
        normalizedNewW, newW, label = initializeW_clustering(OriginaluserNum, relationFileName, nClusters)
        GW = initializeGW_clustering(Gepsilon, relationFileName, newW)
        W = normalizedNewW
    # Read Feature Vectors from File
    FeatureVectors = readFeatureVectorFile(FeatureVectorsFileName)
    # Decide which algorithms to run.

    algorithms = {}

    runCoLinUCB = runGOBLin = runLinUCB = run_M_LinUCB = run_Uniform_LinUCB= run_CFUCB = run_CFEgreedy = run_SGDEgreedy = run_PTS = run_CLUB = run_COFIBA=False
    run_LearnWl2 = run_LearnWl1 = run_LearnWl2_UpdateA = run_LearnWl1_UpdateA = run_LearnW_WRegu =   False
    if args.load:
        fileSig, timeRun = args.load.split('__')
        fileSig = fileSig+'_'
        timeRun = '_'+timeRun
        print (fileSig, timeRun)
        with open(args.load +'.model', 'r') as fin:
            obj = pickle.load(fin)
        with open(args.load +'.txt', 'r') as fin:
            finished_line = int(fin.readline().strip().split()[1])
            print (finished_line)

    if args.alg:
        if args.alg == 'CoLinUCB':
            runCoLinUCB = True
            if args.load:
                algorithms['CoLin'] = obj
            else:
                algorithms['CoLin'] = AsyCoLinUCBAlgorithm(dimension=context_dimension, alpha = alpha, lambda_ = lambda_, n = userNum, W = W)
        elif args.alg == 'CoLinUCBRankOne':
            runCoLinUCB = True
            if args.load:
                algorithms['CoLinRankOne'] = obj
            else:
                algorithms['CoLinRankOne'] = AsyCoLinUCBAlgorithm(dimension=context_dimension, alpha = alpha, lambda_ = lambda_, n = userNum, W = W, update='RankOne')
        elif args.alg == 'GOBLin':
            runGOBLin = True
        elif args.alg == 'CLUB':
            run_CLUB = True
            if args.load:
                algorithms['CLUB'] = obj
            else:
                algorithms['CLUB'] = CLUBAlgorithm(dimension =context_dimension,alpha = alpha, lambda_ = lambda_, n = OriginaluserNum, alpha_2 = alpha_2, cluster_init = 'Erdos-Renyi') 
        elif args.alg == 'COFIBA':
            run_COFIBA = True
            if args.load:
                algorithms['COFIBA'] = obj
            else:
                algorithms['COFIBA'] = COFIBAAlgorithm(dimension =context_dimension,alpha = alpha,  alpha_2 = alpha_2, lambda_ = lambda_, n = OriginaluserNum, itemNum = itemNum,cluster_init = 'Erdos-Renyi') 

        elif args.alg == 'LinUCB':
            runLinUCB = True
            if args.load:
                algorithms['LinUCB'] = obj
            else:
                algorithms['LinUCB'] = N_LinUCBAlgorithm(dimension = context_dimension, alpha = alpha, lambda_ = lambda_, n = OriginaluserNum)
        elif args.alg =='M_LinUCB':
            run_M_LinUCB = True
        elif args.alg == 'Uniform_LinUCB':
            run_Uniform_LinUCB = True
        elif args.alg == 'CFUCB':
            run_CFUCB = True
            if args.load:
                algorithms['CFUCB'] = obj
            else:
                algorithms['CFUCB'] = CFUCBAlgorithm(context_dimension = context_dimension, latent_dimension = latent_dimension, alpha = 0.2, alpha2 = 0.1, lambda_ = lambda_, n = OriginaluserNum, itemNum=itemNum, init='random')
        elif args.alg == 'factorLinUCB':
            if args.load:
                algorithms['factorLinUCB'] = obj
            else:
                algorithms['factorLinUCB'] = FactorLinUCBAlgorithm(context_dimension = context_dimension, latent_dimension = latent_dimension, alpha = 0.2, alpha2 = 0.1, lambda_ = lambda_, n = userNum, itemNum=itemNum, W = W, init='random', window_size = 1)  
        elif args.alg == 'CFEgreedy':
            run_CFEgreedy = True
            if args.load:
                algorithms['CFEgreedy'] = obj
            else:
                algorithms['CFEgreedy'] = CFEgreedyAlgorithm(context_dimension = context_dimension, latent_dimension = latent_dimension, alpha = 200, lambda_ = lambda_, n = OriginaluserNum, itemNum=itemNum, init='random')
        elif args.alg == 'SGDEgreedy':
            run_SGDEgreedy = True
            if not args.dimension:
                dimension = 5
            else:
                dimension = int(args.dimension)
            if args.load:
                algorithms['SGDEgreedy'] = obj
            else:
                algorithms['SGDEgreedy'] = EgreedyContextualStruct(epsilon_init=200, userNum=OriginaluserNum, itemNum=itemNum, k=dimension, feature_dim = context_dimension, lambda_ = lambda_, init='random', learning_rate='constant')
        elif args.alg == 'PTS':
            run_PTS = True
            if not args.particle_num:
                particle_num = 10
            else:
                particle_num = int(args.particle_num)
            if not args.dimension:
                dimension = 10
            else:
                dimension = int(args.dimension)
            if args.load:
                algorithms['PTS'] = obj
            else:
                algorithms['PTS'] = PTSAlgorithm(particle_num = particle_num, dimension = dimension, n = OriginaluserNum, itemNum=itemNum, sigma = np.sqrt(.5), sigmaU = 1, sigmaV = 1)
        elif args.alg == 'UCBPMF': 
            run_UCBPMF = True
            if not args.dimension:
                dimension = 10
            else:
                dimension = int(args.dimension)
            if args.load:
                algorithms['UCBPMF'] = obj
            else:
                algorithms['UCBPMF'] = UCBPMFAlgorithm(dimension = dimension, n = OriginaluserNum, itemNum=itemNum, sigma = np.sqrt(.5), sigmaU = 1, sigmaV = 1, alpha = 0.1) 
        elif args.alg == 'LearnWl1':
            run_LearnWl1 = True
            if args.load:
                algorithms['LearnWl1'] = obj
            else:
                algorithms['LearnWl1'] = LearnWAlgorithm_l1_G(dimension = context_dimension, alpha = alpha, lambda_ = lambda_,  n = userNum, W = W, windowSize = userNum, RankoneInverse=True)
        elif args.alg == 'LearnWl1_UpdateA':
            run_LearnWl1 = True
            if args.load:
                algorithms['LearnWl1_UpdateA'] = obj
            else:
                algorithms['LearnWl1_UpdateA'] = LearnWAlgorithm_l1_G_UpdateA(dimension = context_dimension, alpha = alpha, lambda_ = lambda_,  n = userNum, W = W, windowSize = userNum, RankoneInverse=True)

        elif args.alg == 'LearnWl2':
            run_LearnWl2 = True
            if args.load:
                algorithms['LearnWl2'] = obj
            else:
                algorithms['LearnWl2'] = LearnWAlgorithm_G(dimension = context_dimension, alpha = alpha, lambda_ = lambda_,  n = userNum, W = W, windowSize = userNum, RankoneInverse=True)

        elif args.alg == 'LearnWl2_UpdateA':
            run_LearnWl2_UpdateA = True
            if args.load:
                algorithms['LearnWl2_UpdateA'] = obj
            else:
                algorithms['LearnWl2_UpdateA'] = LearnWAlgorithm_G_UpdateA(dimension = context_dimension, alpha = alpha, lambda_ = lambda_,  n = userNum, W = W, windowSize = userNum, RankoneInverse=True)

        elif args.alg == 'LearnW_WRegu':
            run_LearnWl2_UpdateA = True
            if args.load:
                algorithms['LearnW_WRegu'] = obj
            else:
                algorithms['LearnW_WRegu'] = LearnWAlgorithm_G_WRegu_UpdateA(dimension = context_dimension, alpha = alpha , lambda_ = lambda_,  n = userNum, W = W, windowSize = userNum, RankoneInverse=True)

        elif args.alg == 'ALL':
            runCoLinUCB = runGOBLin = runLinUCB = run_M_LinUCB = run_Uniform_LinUCB=True
    else:
        args.alg = 'Random'
    #runCoLinUCB = runGOBLin = runLinUCB = run_M_LinUCB = run_Uniform_LinUCB= True
    


    if (args.event):
        fileName = args.event
    else:
        fileName = address + "/processed_events_shuffled.dat"
    
    fileSig = 'l2_'+ args.dataset+'_'+args.clusterfile.name.split('/')[-1]+'_shuffled_Clustering_'+args.alg+'_Diagnol_'+args.diagnol+'_'+fileName.split('/')[3]+'_' + str(alpha) + '_' + str(lambda_) + 'Update' + str(UpdateWin)

    articles_random = randomStruct()
    # if args.load:
    #     fileSig, timeRun = args.load.split('__')
    #     fileSig = fileSig+'_'
    #     timeRun = '_'+timeRun
    #     print fileSig, timeRun        
    #     with open(args.load +'.model', 'r') as fin:
    #         obj = pickle.load(fin)
    #     with open(args.load +'.txt', 'r') as fin:
    #         finished_line = int(fin.readline().strip().split()[1])
    #         print finished_line
    #     if runCoLinUCB:
    #         CoLinUCB_USERS = obj
    #     if runGOBLin:
    #         GOBLin_USERS = obj
    #     if runLinUCB:
    #         LinUCB_users = obj
    #     if run_M_LinUCB:
    #         M_LinUCB_users = obj
    #     if run_Uniform_LinUCB:
    #         Uniform_LinUCB_USERS = obj
    # else:
    #     if runCoLinUCB:
    #         CoLinUCB_USERS = CoLinUCBStruct(d, lambda_ ,userNum, W)
    #     if runGOBLin:
    #         GOBLin_USERS = GOBLinStruct(d, lambda_, userNum, GW)

    #     if runLinUCB:
    #         LinUCB_users = []  
    #         for i in range(OriginaluserNum):
    #             LinUCB_users.append(LinUCBStruct(d, lambda_ ))

    #     if run_M_LinUCB:
    #         M_LinUCB_users = []
    #         for i in range(userNum):
    #             M_LinUCB_users.append(LinUCBStruct(d, lambda_))
    #     if run_Uniform_LinUCB:
    #         Uniform_LinUCB_USERS = LinUCBStruct(d, lambda_)

    fileNameWrite = os.path.join(save_address, fileSig + timeRun + '.csv')
    #FeatureVectorsFileName =  LastFM_address + '/Arm_FeatureVectors.dat'

    # put some new data in file for readability
    
    with open(fileNameWrite, 'a+') as f:
        f.write('New Run at  ' + datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'))
        f.write('\n, Time, RandomReward; ')
        for alg_name, alg in algorithms.items():
            f.write(alg_name+'Reward; ')
        f.write('\n')
    print (fileName, fileNameWrite)

    tsave = 60*60*47 # Time interval for saving model.
    tstart = time.time()
    save_flag = 0


    AlgReward = {}
    AlgPicked = {}
    AlgRegret = {}
    for alg_name, alg in algorithms.items():
        AlgReward[alg_name] = []
        AlgPicked[alg_name] = []
        AlgRegret[alg_name] = []
        if not args.load:
            alg.reward = 0

    with open(fileName, 'r') as f:
        f.readline()
        if runLinUCB:
            LinUCBTotalReward  = 0
        # reading file line ie observations running one at a time
        for i, line in enumerate(f, 1):
            if args.load:
                if i< finished_line:
                    continue

            totalObservations +=1            
            OptimalReward = 1
            articlePool = []
            userID, tim, pool_articles = parseLine(line)
            article_chosen = int(pool_articles[0]) 
            for article in pool_articles:
                article_id = int(article.strip(']'))
                articlePool.append(Article(article_id, FeatureVectors[article_id]))

            shuffle(articlePool)

            RandomPicked = choice(articlePool)
            if RandomPicked.id == article_chosen:
                articles_random.reward +=1

            for alg_name, alg in algorithms.items():
                if alg_name in ['CoLin', 'CoLinRankOne','factorLinUCB', 'LearnWl2', 'LearnWl1', 'LearnWl1_UpdateA','LearnWl2_UpdateA', 'LearnW_WRegu']:
                    currentUserID = label[userID]
                else:
                    currentUserID = userID
                pickedArticle = alg.decide(articlePool, currentUserID)
                # reward = getReward(userID, pickedArticle) 
                if (pickedArticle.id == article_chosen):
                    reward = 1
                else:
                    reward = 0
                alg.updateParameters(pickedArticle, reward, currentUserID)

                alg.reward += reward
                AlgReward[alg_name].append(reward)
                AlgPicked[alg_name].append(pickedArticle.id)
                regret = OptimalReward - reward 
                AlgRegret[alg_name].append(regret) 

                if save_flag:
                    model_name = 'saved_models/'+args.dataset+'_'+str(nClusters)+'_shuffled_Clustering_'+alg_name+'_Diagnol_'+args.diagnol+'_' + timeRun
                    model_dump(alg, model_name, i)

            save_flag = 0
            # if the batch has ended
            if totalObservations%batchSize==0:
                printWrite()
                tend = time.time()
                if tend-tstart>tsave:
                    save_flag = 1
                    tstart = tend

    #print stuff to screen and save parameters to file when the Yahoo! dataset file ends
    printWrite()
    model_name = 'saved_models/'+args.dataset+'_'+str(nClusters)+'_shuffled_Clustering_'+alg_name+'_Diagnol_'+args.diagnol+'_' + timeRun
    model_dump(alg, model_name, i)


    
