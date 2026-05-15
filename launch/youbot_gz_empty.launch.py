#!/usr/bin/python3

import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.actions import SetEnvironmentVariable, RegisterEventHandler


from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit


from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import xacro

"""
youbot_gz.launch.py
"""

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default=True)

    youbot_gz_path = get_package_share_directory('youbot_gz')

    world_file = os.path.join(youbot_gz_path, 'world', 'empty_bullet.sdf')


    # youbot_gz_path = <workspace>/install/youbot_gz/share/youbot_gz
    youbot_install = os.path.dirname(os.path.dirname(youbot_gz_path))  # <workspace>/install/youbot_gz
    workspace_src = os.path.join(os.path.dirname(os.path.dirname(youbot_install)), 'src')  # <workspace>/src



    controller_config = os.path.join(youbot_gz_path, 'config', 'youbot_controllers.yaml')

    urdf_file = os.path.join(youbot_gz_path, 'urdf', 'youbot_gz.urdf.xacro')
    doc = xacro.process_file(urdf_file, mappings={'controller_config': controller_config})

    params = {
        'robot_description': doc.toxml(),
        'use_sim_time': use_sim_time
    }

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[params]
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-string', doc.toxml(),
                   '-name', 'youbot',
                   '-allow_renaming', 'true',
                   '-x', '0.0',
                   '-y', '0.0',
                   '-z', '1.10'],
    )

    #### TODO: Add ros2_control launch nodes for youbot control
    load_joint_state_broadcaster = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'joint_state_broadcaster'],
        output='screen'
    )

    load_joint_effort_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active', 'wheel_effort_controller'],
        output='screen'
    )

    return LaunchDescription([
            
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH',
            workspace_src + ':' + 
            os.path.dirname(youbot_gz_path) + ':' +
            os.path.join(youbot_gz_path, 'world')),


        SetEnvironmentVariable('GZ_SIM_SYSTEM_PLUGIN_PATH',
            os.path.join(os.path.expanduser('~'), 'ros2_ws', 'install', 'youbot_gz', 'lib', 'youbot_gz')),

        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_entity,
                on_exit=[load_joint_state_broadcaster],
            )
        ),

        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=load_joint_state_broadcaster,
                on_exit=[load_joint_effort_controller],
            )
        ),

        # Launch gazebo environment
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [os.path.join(get_package_share_directory('ros_gz_sim'),
                              'launch', 'gz_sim.launch.py')]),
            launch_arguments=[('gz_args', [' -r -v 4 ', world_file])]), # remove -r to pause sim


        robot_state_publisher,
        spawn_entity,
        # Launch Arguments
        DeclareLaunchArgument(
            'use_sim_time',
            default_value=use_sim_time,
            description='If true, use simulated clock'),
    ])
