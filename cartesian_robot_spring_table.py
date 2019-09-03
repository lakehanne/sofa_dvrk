import sys
sys.path.insert(1, '../network')

import math
import Sofa
import socket
import numpy as np
from pathlib import Path
import geometry_util as geo

use_network = False
if use_network:
    import torch
    from network import SpringNetwork


class SpringEnv (Sofa.PythonScriptController):
    robot_step = 0
    write_step = 0
    step = 0.05
    axis_scale=100
    time = 0

    # If using network
    input_size = 14
    output_size = 7
    network_path = Path('../network/checkpoints/models/model_80.pt')
    
    # Set so the first position is at centre of the platform
    def __init__(self, node, commandLineArguments) : 
        self.count = 0
        self.commandLineArguments = commandLineArguments
        print("Command line arguments for python : "+str(commandLineArguments))        
#        self.robot_pos = np.genfromtxt('../dataset/test/' + 'data_cartesian_processed.csv', delimiter=',')
        self.robot_pos = np.genfromtxt('../dataset/test/' + 'data1_cartesian_processed.csv', delimiter=',')
        self.createGraph(node)
        self.Instrument.getObject('mecha').position = geo.arrToStr(self.robot_pos[self.robot_step,1:8])
        
    def output(self):
        return


    def populateNonMoving(self, node, filename, translation=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1], mass=1.0, color='red'):
        node.createObject('MeshSTLLoader', name='loader', filename=filename)
        node.createObject('MeshTopology', src='@loader')
        node.createObject('MechanicalObject', name='mecha', src='@loader', scale3d=scale, translation=translation, rotation=rotation)
        node.createObject('TTriangleModel', simulated=0, moving=0)
        node.createObject('TLineModel', simulated=0, moving=0)
        node.createObject('TPointModel', simulated=0, moving=0)
        node.createObject('OglModel', name='visu', src='@loader', scale3d=scale, translation=translation, rotation=rotation, color=color)
        

    def populateRigid(self, node, filename, position=[0,0,0,0,0,0,1], scale=[1, 1, 1], mass=1.0, color='red'):
        node.createObject('EulerImplicitSolver', printLog='false', rayleighStiffness='0.1', name='odesolver', rayleighMass='0.1')
        node.createObject('CGLinearSolver', threshold='1e-9', tolerance='1e-9', name='linearSolver', iterations='25')
        if (filename[-4:] == '.obj'):
            node.createObject('MeshObjLoader', name='loader', filename=filename)
        elif (filename[-4:] == '.STL' or filename[-4:] == '.stl'):
            node.createObject('MeshSTLLoader', name='loader', filename=filename)
        node.createObject('MechanicalObject', name='mecha', template='Rigid3d', scale3d=scale, position=position)
        node.createObject('UniformMass', totalMass=mass)#, showAxisSizeFactor=str(self.axis_scale))
        node.createObject('UncoupledConstraintCorrection')

        # Visual Node
        VisuNode = node.createChild('Visu')
        VisuNode.createObject('OglModel', name='visual', src='@../loader', color=color, scale3d=scale)
        VisuNode.createObject('RigidMapping', input='@../mecha', output='@visual')

        # Collision Node
        CollNode = node.createChild('Coll')
        CollNode.createObject('MeshTopology', src="@../loader")
        CollNode.createObject('MechanicalObject', src='@../loader', name='coll', scale3d=scale, template='Vec3d')
        CollNode.createObject('TTriangleModel')
        CollNode.createObject('TLineModel')
        CollNode.createObject('TPointModel')
        CollNode.createObject('RigidMapping', input='@../mecha', output='@coll')

        return 0    
    
    def populateSpring(self, spring, length, translation, rotation, color='gray'):
#        index = [29575, 29040, 29597]
        spring.createObject('EulerImplicitSolver', printLog='false', rayleighStiffness='0.1', name='odesolver', rayleighMass='0.1')
        spring.createObject('CGLinearSolver', threshold='1e-9', tolerance='1e-9', name='linearSolver', iterations='30')
        spring.createObject('CylinderGridTopology', nx='3', ny='3', length=length, radius='0.425', nz='2', axis='1 0 0', name='topo')
        spring.createObject('MechanicalObject', src='@topo', template='Vec3d', name='spring', rotation=rotation, translation=translation)
#        spring.createObject('TriangularFEMForceFieldOptim', youngModulus='1e3', poissonRatio='0.49')
#        spring.createObject('FastTriangularBendingSprings', bendingStiffness='10000')
        #        spring.createObject('TriangularFEMForceField', youngModulus='1e3', poissonRatio='0.45')
#        spring.createObject('RestShapeSpringsForceField', stiffness=200)
        spring.createObject('TetrahedronFEMForceField', youngModulus='0.006935', poissonRatio='0.45')
#        spring.createObject('MeshSpringForceField', stiffness='1e4', damping='2')
#        spring.createObject('TriangularBendingSprings', youngModulus=5e4, poissonRatio=0.1)
#        spring.createObject('RegularGridSpringForceField', stiffness='1e4', damping='1.0')
        spring.createObject('UniformMass', totalMass=5.0)
        spring.createObject('FixedConstraint', indices=[0, 1, 2, 3, 4, 5, 6, 7, 8])
        spring.createObject('UncoupledConstraintCorrection')
        
        # rootNode/Spring/VisuSpring
        VisuSpring = spring.createChild('VisuSpring')
        VisuSpring.createObject('OglModel', name='visu', src='@../topo', color=color, template='ExtVec3d', rotation=rotation, translation=translation)
        VisuSpring.createObject('BarycentricMapping', input='@../spring', output='@visu')

        return 0
    
    def createGraph(self,rootNode):
        self.rootNode = rootNode
        rootNode.createObject('RequiredPlugin', pluginName='SofaMiscCollision SofaPython')# SofaOpenglVisual') SofaCUDA')
        rootNode.createObject('VisualStyle', displayFlags='showBehaviorModels')# showCollisionModels')# showInteractionForceFields showForceFields')
        rootNode.createObject('FreeMotionAnimationLoop', solveVelocityConstraintFirst=0)
        rootNode.createObject('LCPConstraintSolver', maxIt=1000, tolerance=1e-6, mu=0.9)
        rootNode.createObject('DefaultPipeline', depth=5, verbose=0, draw=0)  
        rootNode.createObject('BruteForceDetection')
        rootNode.createObject('MinProximityIntersection', contactDistance=0.2, alarmDistance=0.2)
        rootNode.createObject('DiscreteIntersection')
        rootNode.createObject('DefaultContactManager', name='Response', response='FrictionContact')

        tableWidth = 95.7
        tableHeight = 72
        
        # rooNode/Support0
        supportHeight = 95.7
        offset = tableWidth/2+16
        height = supportHeight/2
        translation = [-offset, height, 0]
        Support0 = rootNode.createChild('Support0')
        self.populateNonMoving(Support0, 'meshes/lego_support_2.STL', translation=translation, color='blue')
        self.Support0 = Support0

        # rootNode/Support1
        translation = [0, height, -offset]
        rotation = [0, -90, 0]
        Support1 = rootNode.createChild('Support1')
        self.populateNonMoving(Support1, 'meshes/lego_support_2.STL', translation=translation, rotation=rotation, color='blue')
        self.Support1 = Support1

        # rootNode/Support2
        translation = [offset, height, 0]
        rotation = [0, -180, 0]
        Support2 = rootNode.createChild('Support2')
        self.populateNonMoving(Support2, 'meshes/lego_support_2.STL', translation=translation, rotation=rotation, color='blue')
        self.Support2 = Support2

        # rootNode/Support3
        translation = [0, height, offset]
        rotation = [0, -270, 0]
        Support3 = rootNode.createChild('Support3')
        self.populateNonMoving(Support3, 'meshes/lego_support_2.STL', translation=translation, rotation=rotation, color='blue')
        self.Support3 = Support3

        # rootNode/Tabletop
        translation = [0, tableHeight+1, 0]
        Tabletop = rootNode.createChild('Tabletop')
        self.populateRigid(Tabletop, 'meshes/lego_platform_2.STL', position=[0, tableHeight+1, 0, 0, 0, 0, 1], mass=73.6, color='green')
        self.Tabletop = Tabletop

        # rootNode/Spring0
        offset = tableWidth/2+18
        springAngle = 26.5
        springLength = 25 # Should be 20.26 in resting position
        springHeight = tableHeight + 3
        translation = [-offset, springHeight, 0]
        rotation = [0, 0, -springAngle]
        Spring0 = rootNode.createChild('Spring0')
        self.populateSpring(Spring0, springLength, translation, rotation)
        self.Spring0 = Spring0

        # rootNode/Spring1
        translation=[0, springHeight, -offset]
        # Euler angle in XYZ form
        rotation = [-90, 270-springAngle, 90]
        Spring1 = rootNode.createChild('Spring1')
        self.populateSpring(Spring1, springLength, translation, rotation, color='red')
        self.Spring1 = Spring1

        # rootNode/Spring2
        translation=[offset, springHeight, 0]
        rotation = [0, 0, 180+springAngle]
        Spring2 = rootNode.createChild('Spring2')
        self.populateSpring(Spring2, springLength, translation, rotation, color='yellow')
        self.Spring2 = Spring2

        # rootNode/Spring3
        translation=[0, springHeight, offset]
        rotation = [90, 90+springAngle, 90]
        Spring3 = rootNode.createChild('Spring3')
        self.populateSpring(Spring3, springLength, translation, rotation, color='blue')
        self.Spring3 = Spring3
 
#        rootNode.createObject('AttachConstraint', name='ac0', object1='@Tabletop/Coll_Cyl', object2='@Spring0', twoWay='true', indices1='193 242 238 232 591', indices2='10 13 16 12 14', constraintFactor='1 1 1 1 1')
#        rootNode.createObject('AttachConstraint', name='ac1', object1='@Tabletop/Coll_Cyl', object2='@Spring1', twoWay='true', indices1='633 625 626 630 635', indices2='10 13 16 12 14', constraintFactor='1 1 1 1 1', template='Vec3d')
#        rootNode.createObject('AttachConstraint', name='ac2', object1='@Tabletop/Coll_Cyl', object2='@Spring2', twoWay='true', indices1='620 612 613 617 622', indices2='10 13 16 12 14', constraintFactor='1 1 1 1 1', template='Vec3d')
#        rootNode.createObject('AttachConstraint', name='ac3', object1='@Tabletop/Coll_Cyl', object2='@Spring3', twoWay='true', indices1='594 586 587 591 596', indices2='10 13 16 12 14', constraintFactor='1 1 1 1 1', template='Vec3d')

#        rootNode.createObject('BoxStiffSpringForceField', name='ff0', template='Vec3d', stiffness=1e8, object1='@Spring0', object2='@Tabletop/Coll', box_object1='-60 60 -1 -40 70 1', box_object2='-50 60 -1 -40 70 1', forceOldBehavior='false')
#        rootNode.createObject('BoxStiffSpringForceField', name='ff1',  template='Vec3d', stiffness=1e8, object1='@Spring1', object2='@Tabletop/Coll', box_object1='-1 60 -60 1 70 -40', box_object2='-1 60 -50 1 70 -40', forceOldBehavior='false')
#        rootNode.createObject('BoxStiffSpringForceField', name='ff2',  template='Vec3d', stiffness=1e8, object1='@Spring2', object2='@Tabletop/Coll', box_object1='40 60 -1 60 70 1', box_object2='40 60 -1 50 70 1', forceOldBehavior='false')
#        rootNode.createObject('BoxStiffSpringForceField', name='ff3',  template='Vec3d', stiffness=1e8, object1='@Spring3', object2='@Tabletop/Coll', box_object1='-1 60 40 1 70 60', box_object2='-1 60 40 1 70 50', forceOldBehavior='false')
        rootNode.createObject('BoxStiffSpringForceField', name='ff0', template='Vec3d', stiffness=1e8, damping=20, object1='@Support0', object2='@Tabletop/Coll', box_object1='-80 70 -10 -50 100 10', box_object2='-50 60 -1 -40 70 1', forceOldBehavior='false')
        rootNode.createObject('BoxStiffSpringForceField', name='ff1',  template='Vec3d', stiffness=1e8, damping=20,  object1='@Support1', object2='@Tabletop/Coll', box_object1='-10 70 -80 10 100 -50', box_object2='-1 60 -50 1 70 -40', forceOldBehavior='false')
        rootNode.createObject('BoxStiffSpringForceField', name='ff2',  template='Vec3d', stiffness=1e8, damping=20,  object1='@Support2', object2='@Tabletop/Coll', box_object1='50 70 -10 80 100 10', box_object2='40 60 -1 50 70 1', forceOldBehavior='false')
        rootNode.createObject('BoxStiffSpringForceField', name='ff3',  template='Vec3d', stiffness=1e8, damping=20,  object1='@Support3', object2='@Tabletop/Coll', box_object1='-10 70 50 10 100 80', box_object2='-1 60 40 1 70 50', forceOldBehavior='false')

        # rootNode/Instrument
        Instrument = rootNode.createChild('Instrument')
        self.populateRigid(Instrument, 'mesh/sphere.obj', mass=1e3, color='yellow')
        self.Instrument = Instrument
        return 0

    def onMouseButtonLeft(self, mouseX,mouseY,isPressed):
        ## usage e.g.Cylinder
        #    print "Control+Left mouse button pressed at position "+str(mouseX)+", "+str(mouseY)
        return 0

    def onKeyReleased(self, c):
        ## usage e.g.
        #if c=="A" :
        #    print "You released a"
        return 0

    def initGraph(self, node):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        if use_network:
            self.net = SpringNetwork(input_size=self.input_size, output_size=self.output_size)
            # Load previous model if requested
            if self.network_path.exists():
                state = torch.load(str(self.network_path))
                self.net.load_state_dict(state['model'])
                print('Restored model')
            else:
                print('Failed to restore model')
                exit()
            self.net.eval()
        return 0

    # Note: Hold control when key is pressed
    def onKeyPressed(self, c):
        return 0

    def onMouseWheel(self, mouseX,mouseY,wheelDelta):
        ## usage e.g.
        #if isPressed : 
        #    print "Control button pressed+mouse wheel turned at position "+str(mouseX)+", "+str(mouseY)+", wheel delta"+str(wheelDelta)
        return 0

    def storeResetState(self):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        return 0

    def cleanup(self):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        # self.conn.close()
        self.f.close()
        return 0

    def onGUIEvent(self, strControlID,valueName,strValue):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        print 'onGUIEvent'
        return 0

    def onEndAnimationStep(self, deltaTime):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        pos = np.array(self.Tabletop.getObject('mecha').position)
        if use_network:
            robot_pos = self.robot_pos[self.robot_step,1:8]
            updated_pos = self.net(torch.tensor(np.append(robot_pos, pos)).float()).detach().numpy()
            self.Tabletop.getObject('mecha').position = geo.arrToStr(updated_pos)
        self.f.write(str(self.time) + ',' +  geo.arrToStr(pos, delimiter=',') + '\n')
        self.robot_step += 1
        self.time += self.rootNode.findData('dt').value
        
        return 0

    def onLoaded(self, node):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        return 0

    def reset(self):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        self.robot_step = 0
        self.Instrument.getObject('mecha').position = geo.arrToStr(self.robot_pos[self.robot_step,1:8])
        return 0

    def onMouseButtonMiddle(self, mouseX,mouseY,isPressed):
        ## usage e.g.
        #if isPressed : 
        #    print "Control+Middle mouse button pressed at position "+str(mouseX)+", "+str(mouseY)
        return 0

    def bwdInitGraph(self, node):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        self.f = open("measurements/position.txt","w+")
        
        return 0

    def onScriptEvent(self, senderNode, eventName,data):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py
        print 'onScriptEvent'
        return 0

    def onMouseButtonRight(self, mouseX,mouseY,isPressed):
        ## usage e.g.
        #if isPressed :
        #    print "Control+Right mouse button pressed at position "+str(mouseX)+", "+str(mouseY)
        return 0

    def onBeginAnimationStep(self, deltaTime):
        ## Please feel free to add an example for a simple usage in /home/trs/sofa/build/unstable//home/trs/sofa/src/sofa/applications/plugins/SofaPython/scn2python.py

        if (self.robot_step < self.robot_pos.shape[0]):
            self.Instrument.getObject('mecha').position = geo.arrToStr(self.robot_pos[self.robot_step,1:8])
        else:
            self.f.flush()
            self.rootNode.getRootContext().animate = False
        return 0

def createScene(rootNode):
    rootNode.findData('dt').value = '0.01005308'
    rootNode.findData('gravity').value = '0 0 0'
    try : 
        sys.argv[0]
    except :
        commandLineArguments = []
    else :
        commandLineArguments = sys.argv
    my_env = SpringEnv(rootNode,commandLineArguments)
    
    return 0
