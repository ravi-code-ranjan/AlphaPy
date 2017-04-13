################################################################################
#
# Package   : AlphaPy
# Module    : market_flow
# Created   : July 11, 2013
#
# Copyright 2017 ScottFree Analytics LLC
# Mark Conway & Robert D. Scott II
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################


#
# Imports
#

from alphapy.alias import Alias
from alphapy.analysis import Analysis
from alphapy.analysis import run_analysis
from alphapy.data import get_feed_data
from alphapy.globals import PSEP, SSEP
from alphapy.group import Group
from alphapy.market_variables import Variable
from alphapy.market_variables import vmapply
from alphapy.model import get_model_config
from alphapy.model import Model
from alphapy.space import Space

import argparse
import logging
import yaml


#
# Initialize logger
#

logger = logging.getLogger(__name__)


#
# Function get_market_config
#

def get_market_config():
    r"""Read the configuration file for MarketFlow.

    Parameters
    ----------
    None : None

    Returns
    -------
    specs : dict
        The parameters for controlling MarketFlow.

    """

    logger.info("MarketFlow Configuration")

    # Read the configuration file

    full_path = SSEP.join([PSEP, 'config', 'market.yml'])
    with open(full_path, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # Store configuration parameters in dictionary

    specs = {}

    # Section: market [this section must be first]

    specs['forecast_period'] = cfg['market']['forecast_period']
    specs['fractal'] = cfg['market']['fractal']
    specs['leaders'] = cfg['market']['leaders']
    specs['lookback_period'] = cfg['market']['lookback_period']
    specs['predict_date'] = cfg['market']['predict_date']
    specs['schema'] = cfg['market']['schema']
    specs['target_group'] = cfg['market']['target_group']
    specs['train_date'] = cfg['market']['train_date']

    # Create the subject/schema/fractal namespace

    sspecs = ['stock', specs['schema'], specs['fractal']]    
    space = Space(*sspecs)

    # Section: features

    try:
        logger.info("Getting Features")
        specs['features'] = cfg['features']
    except:
        logger.info("No Features Found")
        specs['features'] = {}

    # Section: groups

    try:
        logger.info("Defining Groups")
        for g, m in cfg['groups'].items():
            command = 'Group(\'' + g + '\', space)'
            exec(command)
            Group.groups[g].add(m)
    except:
        logger.info("No Groups Found")

    # Section: aliases

    try:
        logger.info("Defining Aliases")
        for k, v in cfg['aliases'].items():
            Alias(k, v)
    except:
        logger.info("No Aliases Found")

    # Section: system

    try:
        logger.info("Getting System Parameters")
        specs['system'] = cfg['system']
    except:
        logger.info("No System Parameters Found")
        specs['system'] = {}

    # Section: variables

    try:
        logger.info("Defining Variables")
        for k, v in cfg['variables'].items():
            Variable(k, v)
    except:
        logger.info("No Variables Found")

    # Section: functions

    try:
        logger.info("Getting Variable Functions")
        specs['functions'] = cfg['functions']
    except:
        logger.info("No Variable Functions Found")
        specs['functions'] = {}

    # Log the stock parameters

    logger.info('MARKET PARAMETERS:')
    logger.info('features        = %s', specs['features'])
    logger.info('forecast_period = %d', specs['forecast_period'])
    logger.info('fractal         = %s', specs['fractal'])
    logger.info('leaders         = %s', specs['leaders'])
    logger.info('lookback_period = %d', specs['lookback_period'])
    logger.info('predict_date    = %s', specs['predict_date'])
    logger.info('schema          = %s', specs['schema'])
    logger.info('system          = %s', specs['system'])
    logger.info('target_group    = %s', specs['target_group'])
    logger.info('train_date      = %s', specs['train_date'])

    # Market Specifications
    return specs


#
# Function market_pipeline
#

def market_pipeline(model, market_specs):
    r"""AlphaPy MarketFlow Pipeline

    Parameters
    ----------
    model : alphapy.Model
        The model object for AlphaPy.
    market_specs : dict
        The specifications for controlling the MarketFlow pipeline.

    Returns
    -------
    model : alphapy.Model
        The final results are stored in the model object.

    Notes
    -----
    (1) Define a group.
    (2) Get the market data.
    (3) Apply system features.
    (4) Create an analysis.
    (5) Run the analysis, which calls AlphaPy.

    """

    logger.info("Running MarketFlow Pipeline")

    # Get any model specifications
    target = model.specs['target']

    # Get any market specifications

    features = market_specs['features']
    forecast_period = market_specs['forecast_period']
    functions = market_specs['functions']
    leaders = market_specs['leaders']
    lookback_period = market_specs['lookback_period']
    predict_date = market_specs['predict_date']
    target_group = market_specs['target_group']
    train_date = market_specs['train_date']

    # Get the system specifications

    system_name = market_specs['system']['name']
    longentry = market_specs['system']['longentry']
    shortentry = market_specs['system']['shortentry']
    longexit = market_specs['system']['longexit']
    shortexit = market_specs['system']['shortexit']
    holdperiod = market_specs['system']['holdperiod']
    scale = market_specs['system']['scale']

    # Set the target group

    gs = Group.groups[target_group]
    logger.info("All Members: %s", gs.members)

    # Get stock data

    get_feed_data(gs, lookback_period)

    # Apply the features to all of the frames

    vmapply(gs, features, functions)
    vmapply(gs, [target], functions)

    # Run the analysis, including the model pipeline

    a = Analysis(model, gs, train_date, predict_date)
    results = run_analysis(a, forecast_period, leaders)

    # Create and run the system

    cs = System(system_name, longentry, shortentry,
                longexit, shortexit, holdperiod, scale)
    tfs = run_system(model, cs, gs)
 
    # Generate a portfolio
    gen_portfolio(model, system_name, gs, tfs)

    # Return the completed model

    return model


#
# Function main
#

def main(args=None):
    r"""MarketFlow Main Program

    Notes
    -----
    (1) Initialize logging.
    (2) Parse the command line arguments.
    (3) Get the market configuration.
    (4) Get the model configuration.
    (5) Create the model object.
    (6) Call the main MarketFlow pipeline.

    """

    # Logging

    logging.basicConfig(format="[%(asctime)s] %(levelname)s\t%(message)s",
                        filename="market_flow.log", filemode='a', level=logging.DEBUG,
                        datefmt='%m/%d/%y %H:%M:%S')
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s\t%(message)s",
                                  datefmt='%m/%d/%y %H:%M:%S')
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

    # Start the pipeline

    logger.info('*'*80)
    logger.info("MarketFlow Start")
    logger.info('*'*80)

    # Argument Parsing

    parser = argparse.ArgumentParser(description="MarketFlow Parser")
    parser.add_mutually_exclusive_group(required=False)
    parser.add_argument('--predict', dest='predict_mode', action='store_true')
    parser.add_argument('--train', dest='predict_mode', action='store_false')
    parser.set_defaults(predict_mode=False)
    args = parser.parse_args()

    # Read stock configuration file

    market_specs = get_market_config()

    # Read model configuration file

    model_specs = get_model_config()
    model_specs['predict_mode'] = args.predict_mode

    # Create a model from the arguments

    logger.info("Creating Model")
    model = Model(model_specs)

    # Start the pipeline

    model = market_pipeline(model, market_specs)

    # Complete the pipeline

    logger.info('*'*80)
    logger.info("MarketFlow End")
    logger.info('*'*80)


#
# MAIN PROGRAM
#

if __name__ == "__main__":
    main()