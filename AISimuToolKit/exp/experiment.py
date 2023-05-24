"""
@author: Guo Shiguang
@software: PyCharm
@file: experiment.py
@time: 2023/4/18 16:32
"""
import copy
import json
import os
from typing import List

from AISimuToolKit.exp.agents.Courier import Courier
from AISimuToolKit.exp.agents.agent import Agent
from AISimuToolKit.exp.agents.agent_collection import AgentCollection
from AISimuToolKit.exp.scheduler.scheduler import RandomScheduler, SequentialScheduler, BiddingSchedular, \
    DemandScheduler
from AISimuToolKit.model.register import get_model_apis
from AISimuToolKit.store.logger import Logger
from AISimuToolKit.utils.utils import generate_experiment_id, get_fromat_len, parse_yaml_config, save_config

Scheduler = {
    "random": RandomScheduler,
    "sequential": SequentialScheduler,
    "bidding": BiddingSchedular,
    "demand": DemandScheduler
}


class Experiment:
    def __init__(self, id: str, path: str, agents: List[Agent], config: dict):
        self.id = id
        self.path = path
        self.agents = AgentCollection(agents)
        self.scheduler = Scheduler[config["experiment_settings"].get("scheduler")](self.agents,
                                                                                   config["experiment_settings"])
        # config passed in by the user
        self.config = config
        self.logger = Logger()

    def get_agent_ids(self):
        return [agent.agent_id for agent in self.agents]

    @classmethod
    def load(cls,
             config: str,
             model_config: str,
             output_dir: str = "experiments",
             custom_class: dict = None) -> "Experiment":
        """_summary_ Load and instantiate an experiment from a json configuration file

        Args:
            config (str): _description_  The configuration file for the experiment
            model_config (str): _description_ Configure the url for each model
            output_dir (str): _description_  Storage location for logs and history

        Returns:
            _type_: _description_
        """
        # Use the timestamp directly as the experiment ID 
        # no need to checking if the id is duplicate
        exp_id = generate_experiment_id()
        exp_path = Experiment.mk_exp_dir(output_dir, exp_id)
        with open(config, 'r') as file:
            expe_config = json.load(file)
        agents = Experiment.load_agents(agent_list=expe_config['agent_list'], exp_id=exp_id, exp_path=exp_path,
                                        model_config=model_config, expe_settings=expe_config["experiment_settings"],
                                        custom_class=custom_class)
        Courier(agents=agents)
        exp = Experiment(id=exp_id,
                         path=exp_path,
                         agents=agents,
                         config=expe_config)
        save_config(config=expe_config, path=f'{exp.path}/init_config.json')
        return exp

    @staticmethod
    def load_agents(agent_list: List[dict],
                    exp_path: str, exp_id: str,
                    model_config: str, expe_settings: dict, custom_class: dict = None) -> List[Agent]:
        configs = copy.deepcopy(agent_list)
        agents_num = len(configs)
        format_num_len = get_fromat_len(num=agents_num)
        models = get_model_apis(exp_id=exp_id,
                                agents=[i + 1 for i in range(agents_num)],
                                model_names=[config['model_settings']['model_name']
                                             for config in configs],
                                model_config=model_config)
        agents = []
        model_config = parse_yaml_config(model_config)

        Agent_class = Agent
        if custom_class is not None:
            Agent_class = custom_class.get("agent", Agent)

        for idx, config in enumerate(configs):
            if "extra_columns" not in config["misc"]:
                config["misc"]["extra_columns"] = expe_settings.get("extermal_memory_cols", [])
            agents.append(Agent_class.load(
                format_num_len=format_num_len,
                config=config,
                model=models[idx],
                exp_path=exp_path,
                exp_id=exp_id
            ))
        return agents

    @staticmethod
    def mk_exp_dir(output_dir: str, exp_id: str) -> str:
        """"
        Experiment related directory creation
        :return exp root dir 
        """
        exp_path = os.path.join(output_dir, exp_id)
        os.makedirs(exp_path, exist_ok=True)

        # Instantiate a logger to control file location
        logger = Logger(log_file=os.path.join(exp_path, "log.txt"),
                        history_file=os.path.join(exp_path, "history.txt"))
        return exp_path

    def inject_background(self, message: str, prompt: str = "{} {}"):
        """_summary_ 

        Args:
            message (str): _description_
            prompt (str, optional): _description_. Defaults to "{} {}". first is name, second is message
        """
        for agent in self.agents.all():
            agent.receive_info(prompt.format(agent.name, message))
