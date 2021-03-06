import random
import numpy as np
import math
import cPickle
import json
import os
import sys

# Networks
from model.RLLogisticRegression import RLLogisticRegression
from model.NeuralNet import NeuralNet
from model.RLNeuralNetwork import RLNeuralNetwork
from model.RLNeuralNetworkDQ import RLNeuralNetworkDQ
from model.RLDeepNet import RLDeepNet 
from model.DeepCACLA import DeepCACLA
from model.DeepERCACLA import DeepERCACLA
from model.DeepDPG import DeepDPG 
from model.ForwardDynamicsNetwork import ForwardDynamicsNetwork
from model.ImplicitPlanningAgent import ImplicitPlanningAgent

# Games
from game.MapGame import Map
from game.BallGame1D import BallGame1D
from game.BallGame1DFuture import BallGame1DFuture
from game.BallGame1DState import BallGame1DState
from game.BallGame1DChoiceState import BallGame1DChoiceState
from game.BallGame1DChoiceStateFuture import BallGame1DChoiceStateFuture
from game.BallGame2DChoice import BallGame2DChoice
from game.BallGame2D import BallGame2D

from RL_visualizing import *
from RLVisualize import RLVisualize
from NNVisualize import NNVisualize
from model.ExperienceMemory import ExperienceMemory 



    
if __name__ == "__main__":

    # make a color map of fixed colors
    #try: 
        file = open(sys.argv[1])
        settings = json.load(file)
        file.close()
        map = loadMap()
        # Normalization constants for data
        max_reward = settings['max_reward']
        # max_reward = 1.0
        state_bounds = np.array(settings['state_bounds'])
        state_length = len(state_bounds[0])
        
        print "Max Reward: " + str(max_reward)
        print "State Bounds: " + str(state_bounds)
        
        
        # game = Map(map)
        game = None
        game_type = settings['game_type']
        if game_type == 'BallGame1DFuture':
            print "Starting game type: " + str(game_type)
            game = BallGame1DFuture()
        elif game_type == 'BallGame1D':
            print "Starting game type: " + str(game_type)
            game = BallGame1D()
        elif game_type == 'BallGame1DState':
            print "Starting game type: " + str(game_type)
            game = BallGame1DState()
            visualize_policy=False
        elif game_type == 'BallGame1DChoiceState':
            print "Starting game type: " + str(game_type)
            game = BallGame1DChoiceState()
            visualize_policy=False
        elif game_type == 'BallGame1DChoiceStateFuture':
            print "Starting game type: " + str(game_type)
            game = BallGame1DChoiceStateFuture()
            visualize_policy=False
        elif game_type == 'BallGame2D':
            print "Starting game type: " + str(game_type)
            game = BallGame2D()
            visualize_policy=False    
        elif game_type == 'BallGame2DChoice':
            print "Starting game type: " + str(game_type)
            game = BallGame2DChoice()
            visualize_policy=False
        else:
            print "Unrecognized game: " + str(game_type)
            sys.exit()
            
        # game.enableRender()
        # game._simulate=True
        # game._saveVideo=True
        game.setMovieName(str(settings['agent_name']) + "_on_" + str(game_type))
            
        action_bounds = np.array(settings['action_bounds'])
        action_length = len(action_bounds[0])
        data_folder = settings['data_folder']
        states = np.array([state_bounds[1]])
        action_space_continuous=True
        
        file_name=data_folder+"navigator_agent_"+str(settings['agent_name'])+".pkl"
        model = cPickle.load(open(file_name))
        
        file_name_dynamics=data_folder+"forward_dynamics_"+str(settings['agent_name'])+".pkl"
        forwardDynamicsModel = cPickle.load(open(file_name_dynamics))
        """
        if action_space_continuous:
            # X, Y, U, V, Q = get_continuous_policy_visual_data(model, state_bounds, game)
            X, Y, U, V, Q = get_continuous_policy_visual_data1D(model, state_bounds, game)
        else:
            X, Y, U, V, Q = get_policy_visual_data(model, state_bounds, game)
        game.init(U, V, Q)
        """
        game.init(np.random.rand(16,16),np.random.rand(16,16),np.random.rand(16,16))
        game.reset()
        
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        num_actions = 200
        scaling = 1.0
        game._box.state[0][1] = 0.0
        reward_sum=0
        actions = (np.random.rand(num_actions,1)-0.5) * 2.0 * scaling
        for action_ in actions:
            # ballGame.resetTarget()
            game.resetTarget()
            game.resetHeight()
            game._box.state[0][1] = 0.0
            state = game.getState()
            print "State: " + str(state)
            # reward = game.actContinuous(action_)
            # print "Action: " + str(action_)
            # print "Verify State: " + str(state) + " with " + str(scale_state(norm_state(state, max_state=state_bounds), max_state=state_bounds))
            """
            if action_space_continuous:
                # X, Y, U, V, Q = get_continuous_policy_visual_data(model, state_bounds, game)
                X, Y, U, V, Q = get_continuous_policy_visual_data1D(model, state_bounds, game)
            else:
                X, Y, U, V, Q = get_policy_visual_data(model, state_bounds, game)
            game.updatePolicy(U, V, Q)
            """
            pa = model.predict([norm_state(state, state_bounds)])
            if action_space_continuous:
                action = scale_action(pa, action_bounds)
                print "Action: " + str(action)
                prediction = scale_state(forwardDynamicsModel.predict(state=norm_state(state, state_bounds), action=norm_action(action, action_bounds)), state_bounds)
                print "Next State Prediction: " + str(prediction)
                predicted_height = game._computeHeight(prediction[1]) # This is dependent on the network shape
                game.setPrediction([2,predicted_height])
                # print "Next Height Prediction: " + str(predicted_height)
                reward = game.actContinuous(action)
                print "Height difference: " + str(math.fabs(predicted_height - game._max_y))
            elif not action_space_continuous:
                # print "Action: " + str(pa)
                reward = game.act(action)
            reward_sum+=reward
            # print "Reward: " + str(reward)
            
        print "Average reward: " + str(reward_sum/num_actions)
            
            

    #except Exception, e:
    #    print "Error: " + str(e)
    #    raise e
