import theano
from theano import tensor as T
import numpy as np
from theano.sandbox.rng_mrg import MRG_RandomStreams as RandomStreams
import lasagne
from theano.ifelse import ifelse

# For debugging
# theano.config.mode='FAST_COMPILE'
srng = RandomStreams()

def floatX(X):
    return np.asarray(X, dtype=theano.config.floatX)

def init_weights(shape):
    return theano.shared(floatX(np.random.randn(*shape) * 0.5))

def init_b_weights(shape):
    return theano.shared(floatX(np.random.randn(*shape) * 0.1), broadcastable=(True, False))

def init_tanh(n_in, n_out):
    rng = np.random.RandomState(1234)
    return theano.shared(np.asarray(
                rng.uniform(
                    low=-np.sqrt(6. / (n_in + n_out)),
                    high=np.sqrt(6. / (n_in + n_out)),
                    size=(n_in, n_out)
                ),
                dtype=theano.config.floatX
            ))

def sgd(cost, params, lr=0.05):
    grads = T.grad(cost=cost, wrt=params)
    updates = []
    for p, g in zip(params, grads):
        updates.append([p, p + (-g * lr)])
    return updates

def rlTDSGD(cost, delta, params, lr=0.05):
    grads = T.grad(cost=cost, wrt=params)
    updates = []
    for p, g in zip(params, grads):
        updates.append([p, p + (lr * delta * g)])
    return updates

def rectify(X):
    # return X
    return T.maximum(X, 0.)

def perceptron(X):
    return X

def RMSprop(cost, params, lr=0.001, rho=0.95, epsilon=0.01):
    grads = T.grad(cost=cost, wrt=params)
    updates = []
    for p, g in zip(params, grads):
        acc = theano.shared(p.get_value() * 0.)
        acc_new = rho * acc + (1 - rho) * g ** 2
        gradient_scaling = T.sqrt(acc_new + epsilon)
        g = g / gradient_scaling
        updates.append((acc, acc_new))
        updates.append((p, p - (lr * g)))
    return updates

def RMSpropRL(cost, delta, params, lr=0.001, rho=0.95, epsilon=0.01):
    grads = T.grad(cost=cost, wrt=params)
    updates = []
    for p, g in zip(params, grads):
        print "grad: " + str(g)
        print "p: " + str(p)
        acc = theano.shared(p.get_value() * 0.0)
        acc_new = rho * acc + (1 - rho) * g ** 2
        gradient_scaling = T.sqrt(acc_new + epsilon)
        g = g / gradient_scaling
        print acc
        print acc_new
        print g
        print p
        updates.append((acc, acc_new))
        updates.append((p, p + (lr * delta * g)))
    return updates


def dropout(X, p=0.):
    p=0.0 # disabled dropout
    if p > 0:
        retain_prob = 1 - p
        X *= srng.binomial(X.shape, p=retain_prob, dtype=theano.config.floatX)
        X /= retain_prob
    return X

class RLNeuralNetworkDQ(object):
    
    def __init__(self, input, n_in, n_out):

        hidden_size=36
        batch_size=32
        self._w_h = init_weights((n_in, hidden_size))
        self._b_h = init_b_weights((1,hidden_size))
        # self._b_h = init_b_weights((hidden_size,))
        self._w_h2 = init_weights((hidden_size, hidden_size))
        self._b_h2 = init_b_weights((1,hidden_size))
        # self._b_h2 = init_b_weights((hidden_size,))
        # self._w_o = init_tanh(hidden_size, n_out)
        self._w_o = init_weights((hidden_size, n_out))
        self._b_o = init_b_weights((1,n_out))
        # self._b_o = init_b_weights((n_out,))
        
        self.updateTargetModel()
        self._w_h_old = init_weights((n_in, hidden_size))
        self._w_h2_old = init_weights((hidden_size, hidden_size))
        self._w_o_old = init_tanh(hidden_size, n_out)

        
        # print "Initial W " + str(self._w_o.get_value()) 
        
        self._learning_rate = 0.00025
        self._discount_factor= 0.99
        
        self._weight_update_steps=5000
        self._updates=0
        
        
        # data types for model
        State = T.dmatrix("State")
        State.tag.test_value = np.random.rand(batch_size,2)
        ResultState = T.dmatrix("ResultState")
        ResultState.tag.test_value = np.random.rand(batch_size,2)
        Reward = T.col("Reward")
        Reward.tag.test_value = np.random.rand(batch_size,1)
        Action = T.icol("Action")
        Action.tag.test_value = np.zeros((batch_size,1),dtype=np.dtype('int32'))
        # Q_val = T.fmatrix()
        
        # model = T.nnet.sigmoid(T.dot(State, self._w) + self._b.reshape((1, -1)))
        # self._model = theano.function(inputs=[State], outputs=model, allow_input_downcast=True)
        _py_xA = self.model(State, self._w_h, self._b_h, self._w_h2, self._b_h2, self._w_o, self._b_o, 0.0, 0.0)
        _py_xB = self.model(State, self._w_h_old, self._b_h_old, self._w_h2_old, self._b_h2_old, self._w_o_old, self._b_o_old, 0.0, 0.0)
        self._y_predA = T.argmax(_py_xA, axis=1)
        self._y_predB = T.argmax(_py_xB, axis=1)
        self._q_funcA = T.mean((self.model(State, self._w_h, self._b_h, self._w_h2, self._b_h2, self._w_o, self._b_o, 0.0, 0.0))[T.arange(batch_size), Action.reshape((-1,))].reshape((-1, 1)))
        self._q_funcB = T.mean((self.model(State, self._w_h_old, self._b_h_old, self._w_h2_old, self._b_h2_old, self._w_o_old, self._b_o_old, 0.0, 0.0))[T.arange(batch_size), Action.reshape((-1,))].reshape((-1, 1)))
        # q_val = py_x
        # noisey_q_val = self.model(ResultState, self._w_h, self._b_h, self._w_h2, self._b_h2, self._w_o, self._b_o, 0.2, 0.5)
        
        # L1 norm ; one regularization option is to enforce L1 norm to
        # be small
        self._L1_A = (
            abs(self._w_h).sum() +
            abs(self._w_h2).sum() +
            abs(self._w_o).sum()
        )
        self._L1_B = (
            abs(self._w_h_old).sum() +
            abs(self._w_h2_old).sum() +
            abs(self._w_o_old).sum()
        )
        self._L1_reg= 0.0
        self._L2_reg= 0.001
        # L2 norm ; one regularization option is to enforce
        # L2 norm to be small
        self._L2_A = (
            (self._w_h ** 2).sum() +
            (self._w_h2 ** 2).sum() +
            (self._w_o ** 2).sum()
        )
        self._L2_B = (
            (self._w_h_old ** 2).sum() +
            (self._w_h2_old ** 2).sum() +
            (self._w_o_old ** 2).sum()
        )
        
        # cost = T.mean(T.nnet.categorical_crossentropy(py_x, Y))
        # delta = ((Reward.reshape((-1, 1)) + (self._discount_factor * T.max(self.model(ResultState), axis=1, keepdims=True)) ) - self.model(State))
        deltaA = ((Reward + (self._discount_factor * 
                            T.max(self.model(ResultState, self._w_h_old, self._b_h_old, self._w_h2_old, self._b_h2_old, self._w_o_old, self._b_o_old, 0.2, 0.5), axis=1, keepdims=True)) ) - 
                            (self.model(State, self._w_h, self._b_h, self._w_h2, self._b_h2, self._w_o, self._b_o, 0.2, 0.5))[T.arange(Action.shape[0]), Action.reshape((-1,))].reshape((-1, 1)))
        deltaB = ((Reward + (self._discount_factor * 
                            T.max(self.model(ResultState, self._w_h, self._b_h, self._w_h2, self._b_h2, self._w_o, self._b_o, 0.2, 0.5), axis=1, keepdims=True)) ) - 
                            (self.model(State, self._w_h_old, self._b_h_old, self._w_h2_old, self._b_h2_old, self._w_o_old, self._b_o_old, 0.2, 0.5))[T.arange(Action.shape[0]), Action.reshape((-1,))].reshape((-1, 1)))
        # bellman_cost = T.mean( 0.5 * ((delta) ** 2 ))
        bellman_costA = T.mean( 0.5 * ((deltaA) ** 2 )) + ( self._L2_reg * self._L2_A) + ( self._L1_reg * self._L1_A)
        bellman_costB = T.mean( 0.5 * ((deltaB) ** 2 )) + ( self._L2_reg * self._L2_B) + ( self._L1_reg * self._L1_B)

        paramsA = [self._w_h, self._b_h, self._w_h2, self._b_h2, self._w_o, self._b_o]
        paramsB = [self._w_h_old, self._b_h_old, self._w_h2_old, self._b_h2_old, self._w_o_old, self._b_o_old]
        # updates = sgd(bellman_cost, params, lr=self._learning_rate)
        updatesA = rlTDSGD(self._q_funcA, T.mean(deltaA), paramsA, lr=self._learning_rate)
        updatesB = rlTDSGD(self._q_funcB, T.mean(deltaB), paramsB, lr=self._learning_rate)
        # updates = RMSprop(bellman_cost, params, lr=self._learning_rate)
        # updates = RMSpropRL(q_func, T.mean(delta), params, lr=self._learning_rate)
        # updates = lasagne.updates.rmsprop(bellman_cost, params, self._learning_rate, 0.95, 0.01)
        # updatesA = lasagne.updates.rmsprop(self._q_funcA, paramsA, self._learning_rate * -T.mean(deltaA), 0.95, 0.01)
        # updatesB = lasagne.updates.rmsprop(self._q_funcB, paramsB, self._learning_rate * -T.mean(deltaB), 0.95, 0.01)
        
        self._trainA = theano.function(inputs=[State, Action, Reward, ResultState], outputs=bellman_costA, updates=updatesA, allow_input_downcast=True)
        self._trainB = theano.function(inputs=[State, Action, Reward, ResultState], outputs=bellman_costB, updates=updatesB, allow_input_downcast=True)
        self._bellman_errorA = theano.function(inputs=[State, Action, Reward, ResultState], outputs=deltaA, allow_input_downcast=True)
        self._bellman_errorB = theano.function(inputs=[State, Action, Reward, ResultState], outputs=deltaB, allow_input_downcast=True)
        self._q_valuesA = theano.function(inputs=[State], outputs=_py_xA, allow_input_downcast=True)
        self._q_valuesB = theano.function(inputs=[State], outputs=_py_xB, allow_input_downcast=True)
        self._py_xA = theano.function(inputs=[State], outputs=_py_xA, allow_input_downcast=True)
        self._py_xB = theano.function(inputs=[State], outputs=_py_xB, allow_input_downcast=True)
        
        x,y = T.matrices('x', 'y')
        z_lazy = ifelse(T.gt(T.max(x, axis=1)[0], T.max(y, axis=1)[0]), T.argmax(x, axis=1), T.argmax(y, axis=1))
        self._f_lazyifelse = theano.function([x, y], z_lazy,
                               mode=theano.Mode(linker='vm'))
        
        
    def model(self, State, w_h, b_h, w_h2, b_h2, w_o, b_o, p_drop_input, p_drop_hidden):
        State = dropout(State, p_drop_input)
        h = rectify(T.dot(State, w_h) + b_h)
    
        h = dropout(h, p_drop_hidden)
        h2 = rectify(T.dot(h, w_h2) + b_h2)
    
        h2 = dropout(h2, p_drop_hidden)
        # q_val_x = T.tanh(T.dot(h2, w_o) + b_o)
        q_val_x = rectify(T.dot(h2, w_o) + b_o)
        # q_val_x = perceptron(T.dot(h2, w_o) + b_o)
        # q_val_x = T.nnet.sigmoid(T.dot(h2, w_o) + b_o)
        return q_val_x
    
    def updateTargetModel(self):
        print "Updating target Model"
        self._w_h_old = self._w_h 
        self._b_h_old = self._b_h 
        self._w_h2_old = self._w_h2
        self._b_h2_old = self._b_h2
        self._w_o_old = self._w_o 
        self._b_o_old = self._b_o 
    
    def train(self, state, action, reward, result_state):
        import random
        r = random.choice([0,1])
        if r == 0:
            return self._trainA(state, action, reward, result_state)
        else:
            return self._trainB(state, action, reward, result_state)
    
    def predict(self, state):
        
        return self._f_lazyifelse(self._py_xA(state), self._py_xB(state))

    def q_values(self, state):
        return self._q_valuesA(state)
        # return np.max(np.append(self._q_valuesA(state), self._q_valuesB(state), axis=0),axis=0)
        # return [self.q_valuesA(state),self.q_valuesB(state)] 
    def bellman_error(self, state, action, reward, result_state):
        return self._bellman_errorA(state, action, reward, result_state)
