import os

from aztarna.commons import RobotAdapter
from aztarna.ros.ros2.helpers import ROS2Node, ROS2Host, ROS2Topic

default_topics = ['/rosout', '/parameter_events']


class ROS2Scanner(RobotAdapter):

    def __init__(self):
        super().__init__()
        self.found_hosts = []
        self.scanner_node_name = 'aztarna'

    def scan_pipe_main(self):
        raise NotImplementedError

    def print_results(self):
        for host in self.found_hosts:
            print(f'[+] Host found in Domain ID {host.domain_id}')
            print('\tTopics:')
            for topic in host.topics:
                print(f'\t\tTopic Name: {topic.name} \t|\t Topic Type: {topic.topic_type}')
            print('\tNodes:')
            for node in host.nodes:
                print(f'\t\tNode Name: {node.name} \t|\t Namespace: {node.namespace}')
                if self.extended:
                    self.print_node_topics(node)
            print('-' * 80)

    @staticmethod
    def print_node_topics(node):
        print(f'\t\tPublished topics:')
        for topic in node.published_topics:
            print(f'\t\t\tTopic Name: {topic.name} \t|\t Topic Type: {topic.topic_type}')
        print('\t\tSubscribed topics:')
        for topic in node.subscribed_topics:
            print(f'\t\t\tTopic Name: {topic.name} \t|\t Topic Type: {topic.topic_type}')

    def write_to_file(self, out_file):
        lines = []
        header = 'DomainID;NodeName;Namespace;Topic;TopicType;Direction\n'
        lines.append(header)
        with open(out_file, 'w') as f:
            for host in self.found_hosts:
                if self.extended:
                    for node in host.nodes:
                        self.write_node_topics(host, lines, node)
                else:
                    for topic in host.topics:
                        line = f'{host.domain_id};;{topic.name};{topic.topic_type};;\n'
                        lines.append(line)
            f.writelines(lines)

    @staticmethod
    def write_node_topics(host, lines, node):
        for published_topic in node.published_topics:
            line = f'{host.domain_id};{node.name};{node.namespace};{published_topic.name};' \
                f'{published_topic.topic_type};Publish\n'
            lines.append(line)
        for subscribed_topic in node.subscribed_topics:
            line = f'{host.domain_id};{node.name};{node.namespace};{subscribed_topic.name};' \
                f'{subscribed_topic.topic_type};Subscribe\n'
            lines.append(line)

    def scan(self):
        try:
            import rclpy
        except ImportError:
            raise Exception('ROS2 needs to be installed and sourced to run ROS2 scans')

        for i in range(0, 255):
            os.environ['ROS_DOMAIN_ID'] = str(i)
            rclpy.init()
            scanner_node = rclpy.create_node(self.scanner_node_name)
            found_nodes = self.scan_ros2_nodes(scanner_node)
            if found_nodes:
                host = ROS2Host()
                host.domain_id = i
                host.nodes = found_nodes
                host.topics = self.scan_ros2_topics(scanner_node)
                if self.extended:
                    for node in found_nodes:
                        self.get_node_topics(scanner_node, node)
                self.found_hosts.append(host)
            rclpy.shutdown()
        return self.found_hosts

    def scan_ros2_nodes(self, scanner_node):
        nodes = scanner_node.get_node_names_and_namespaces()
        found_nodes = []
        for node_name, namespace in nodes:
            if node_name != self.scanner_node_name:
                found_node = ROS2Node()
                found_node.name = node_name
                found_node.namespace = namespace
                found_nodes.append(found_node)
        return found_nodes

    def scan_ros2_topics(self, scanner_node):
        topics = scanner_node.get_topic_names_and_types()
        return self.raw_topics_to_pyobj_list(topics)

    def get_node_topics(self, scanner_node, node):
        published_topics = scanner_node.get_publisher_names_and_types_by_node(node.name, node.namespace)
        subscribed_topics = scanner_node.get_subscriber_names_and_types_by_node(node.name, node.namespace)
        node.published_topics = self.raw_topics_to_pyobj_list(published_topics)
        node.subscribed_topics = self.raw_topics_to_pyobj_list(subscribed_topics)

    @staticmethod
    def raw_topics_to_pyobj_list(topics, include_default=False):
        topics_list = []
        for topic_name, topic_type in topics:
            if not (not include_default and topic_name in default_topics):
                topic = ROS2Topic()
                topic.name = topic_name
                topic.topic_type = topic_type
                topics_list.append(topic)
        return topics_list
