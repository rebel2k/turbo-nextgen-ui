#from urllib import response
import requests
import urllib3
import json
from datetime import datetime
import streamlit as st
import plotly.express as px
#import plotly.figure_factory as ff
import pandas as pd

urllib3.disable_warnings()

# Global variables
authentication_token = ''
turboserver = ''
vms = {}
stats = {}

# Global Config
st.set_page_config(layout="wide")
vms_cursor_steps = 500
actions_cursor_steps = 100

def set_turboserver(server_address):
    global turboserver
    turboserver = server_address
    
def authenticate_user(username, password):
    # Authentication of the user
    authentication_payload = {'username': username, 'password': password}
    #print(authentication_payload)
    r = requests.post('https://'+turboserver+'/api/v3/login', data = authentication_payload, verify=False)
    #print(r.status_code)
    #print(r.text)
    if (r.status_code == 200):
        r.encoding = 'JSON'
        token = r.headers['Set-Cookie'].split(';')[0]
        # print(token)
        global authentication_token
        authentication_token = token
    return r.status_code

def get_vms_list(): 
    # Get list of On-Prem VMs and store them
    vms = {}
    i = 0
    max_entities = 1 # initialization for first loop
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'cookie': authentication_token}
    #url = 'https://'+turboserver+'/api/v3/search?types=VirtualMachine&entity_types=VirtualMachine&cursor='+str(i)+'&limit='+str(cursor_steps)+'&detail_type=aspects&order_by=NAME&ascending=true'
    url = 'https://'+turboserver+'/api/v3/search?types=VirtualMachine&entity_types=VirtualMachine&environment_type=ONPREM&cursor='+str(i)+'&limit='+str(vms_cursor_steps)+'&detail_type=entity&order_by=NAME&ascending=true'
    while i < max_entities:
        r = requests.get(url, headers = headers, verify=False)
        max_entities = int(r.headers['X-Total-Record-Count'])
        # print("Max entities: "+str(max_entities))
        # print("Cursor: "+str(i))
        # print("Status code: "+str(r.status_code))
        # print("Content: "+r.text)
        response_dict = json.loads(r.text) # Load the result in a dict
        # columns definition
        #time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        time = datetime.now().strftime("%d/%m/%Y %H:%M")
        vm_uuid = ''
        vm_name = ''
        host_uuid = ''
        host_name = ''
        for vm in response_dict:
            # print("VM: " + vm['uuid'] + " - " + vm['displayName']+ " - " + vm['className'] +  " - " +  vm['environmentType'])
            if (vm['environmentType'] == "ONPREM"): # fix to make sure HYBRID environmentType are not parsed (bug introduced in the API in 8.6.3)
                vm_uuid = vm['uuid']
                vm_name = vm['displayName']
                # vm_environment = vm['environmentType']
                # print("VM UUID: " + vm_uuid + " - VM Name: " + vm_name)
                for provider in vm['providers']:
                    #print("Provider: " + provider['uuid'] + " - " + provider['displayName'] + " - " + provider['className'])
                    if (provider['className'] == "PhysicalMachine"):
                        # print("Provider: " + provider['uuid'] + " - " + provider['displayName'] + " - " + provider['className'])
                        host_uuid = provider['uuid']
                        host_name = provider['displayName']
                # Prepare the record
                # print(time + " - " + vm_uuid + " - " + vm_name + " - " + host_uuid + " - " + host_name)
                # Store the VM in a dictionary
                vms[vm_uuid] = vm_name + " # " + vm_uuid
                #vms.append(vm_name + " - " + vm_uuid)
        i += vms_cursor_steps+1
    return vms

def get_stats_list(entity):
    # Get VCPU stats of the selected VM and store them
    stats_list = []
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'cookie': authentication_token}
    url = 'https://'+turboserver+'/api/v3/entities/'+entity+'/stats'
    r = requests.get(url, headers = headers, verify=False)
    # print("Payload: "+str(payload))
    # print("Status code: "+str(r.status_code))
    # print("Content: "+r.text)
    json_stats = r.json()
    for line in json_stats:
        for stat in line['statistics']:
            stats_list.append(stat['name'])
    #print(stats_list)
    return stats_list

def get_stats(entity, stats_list_array, timeframe):
    # Get stats of the selected VM and store them
    stats = {}
    stats_list = []
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'cookie': authentication_token}
    #payload = "{ \"scopes\": [ \"" + stats_entity + "\" ], \"period\": { \"startDate\": \"-2h\", \"statistics\": [ { \"name\": \"VCPU\"}, {\"name\": \"VMem\" }] }, \"relatedType\": \"VirtualMachine\" }"
    #url = 'https://'+turboserver+'/api/v3/stats'
    for stat in stats_list_array:
        stats_list.append({"name": stat, "relatedEntityType": "VirtualMachine"})
    #print(json.dumps(stats_list))
    #print(stats_list)
    payload = "{\"statistics\":"+json.dumps(stats_list)+",\"startDate\":\""+timeframe+"\"}"
    url = 'https://'+turboserver+'/api/v3/stats/'+entity

    r = requests.post(url, headers = headers, data = payload, verify=False)
    #print("Payload: "+str(payload))
    # print("Status code: "+str(r.status_code))
    # print("Content: "+r.text)

    json_stats = r.json()
    #print(json_stats)
    dates = []
    values = []
    for line in json_stats:
        line_date = line['date']
        line_value = line['statistics'][0]['value']
        #print(line_value)
        dates.append(line_date)
        if not (line['statistics'][0].get("capacity") is None): # To make sure there's a capacity section (for certain metric it's not the case)
            line_capacity = line['statistics'][0]['capacity']['total']
            #print(line_capacity)
            values.append(line_value/line_capacity*100)
        else: # if there's no capacity, just return the value
            #print("Doesn't exist")
            values.append(line_value)
        #stats[line_date] = line_value
    #print(stats)
    index = pd.DatetimeIndex(dates)
    #print(index)
    data = pd.Series(values, index = index, name = stats_type, dtype="float64")
    #print(data)
    return data

def get_tags(entity):
    tags = {}
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'cookie': authentication_token}
    url = 'https://'+turboserver+'/api/v3/entities/'+entity+'/tags'
    r = requests.get(url, headers = headers, verify=False)
    # print("Payload: "+str(payload))
    # print("Status code: "+str(r.status_code))
    # print("Content: "+r.text)
    json_stats = r.json()
    for tag in json_stats:
        #print("Key: "+tag['key'])
        key = tag['key']
        tags[key] = tag['values']
    tags_df = pd.DataFrame.from_dict(tags).transpose()
    return tags_df

def get_actions(entity):
    actions = {}
    i = 0
    max_actions = 1 # initialization for first loop
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'cookie': authentication_token}
    url = 'https://'+turboserver+'/api/v3/entities/'+entity+'/actions?detail_level=STANDARD&cursor='+str(i)+'&limit='+str(actions_cursor_steps)+'&order_by=RISK_CATEGORY&ascending=false'
    while i < max_actions:
        r = requests.get(url, headers = headers, verify=False)
        max_actions = int(r.headers['X-Total-Record-Count'])
        # print("Payload: "+str(payload))
        # print("Status code: "+str(r.status_code))
        # print("Content: "+r.text)
        json_stats = r.json()
        for action in json_stats:
            action_uuid = action['uuid']
            action_type = action['actionType']
            action_mode = action['actionMode']
            action_details = action['details']
            action_category = action['risk']['subCategory']
            actions[action_uuid] = {'uuid': action_uuid, 'details': action_details, 'type': action_type, 'mode': action_mode, 'category': action_category}
        i += actions_cursor_steps+1
    actions_df = pd.DataFrame.from_dict(actions).transpose()
    #print(actions_df)
    return actions_df

def get_placement_policies():
    policies = {}
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'cookie': authentication_token}
    url = 'https://'+turboserver+'/api/v3/markets/Market/policies'
    r = requests.get(url, headers = headers, verify=False)
    #print("Status code: "+str(r.status_code))
    #print("Content: "+r.text)
    json_stats = r.json()
    for policy in json_stats:
        policy_uuid = policy['uuid']
        policy_name = policy['displayName']
        policy_type = policy['type']
        policy_state = policy['enabled']
        policies[policy_uuid] = {'name': policy_name, 'type': policy_type, 'state': policy_state}
    # print(type(policies))
    # print(policies)
    policies_df = pd.DataFrame.from_dict(policies).transpose()
    return policies_df

def get_automation_policies():
    policies = {}
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'cookie': authentication_token}
    url = 'https://'+turboserver+'/api/v3/settingspolicies'
    r = requests.get(url, headers = headers, verify=False)
    #print("Status code: "+str(r.status_code))
    #print("Content: "+r.text)
    json_stats = r.json()
    for policy in json_stats:
        policy_uuid = policy['uuid']
        policy_name = policy['displayName']
        policy_type = policy['entityType']
        policy_default = policy['default']
        policy_readonly = policy['readOnly']
        policy_state = True if policy['disabled'] == False else False
        policies[policy_uuid] = {'name': policy_name, 'type': policy_type, 'state': policy_state, 'is_default': policy_default, 'is_readonly': policy_readonly}
    # print(type(policies))
    # print(policies)
    policies_df = pd.DataFrame.from_dict(policies).transpose()
    return policies_df

def main():

    global vms

    # --- Initialising SessionState ---
    if "authentication_state" not in st.session_state:
     st.session_state.authentication_state = False

    # Rendering in the UI
    st.title(""" Turbonomic Nextgen UI """)
    menubar = st.sidebar

    menubar.write("This is a Work In Progress Mockup of a new Turbonomic UI based on REST API calls")
    menubar.title(""" Menu """)
    login_container = menubar.container()
    selected_page = menubar.selectbox("Page", ["Metrics", "Policies"])

    #login_container = st.container()
    #col1, col2, col3, col4 = login_container.columns(4)
    # server_address = col1.text_input("Turbonomic Server")
    # username = col2.text_input("Username")
    # password = col3.text_input("Password", type="password")
    # login_checkbox = col4.checkbox("Login")

    server_address = login_container.text_input("Turbonomic Server")
    username = login_container.text_input("Username")
    password = login_container.text_input("Password", type="password")
    #login_checkbox = login_container.checkbox("Login")
    login_button = login_container.button('Login')
    if login_button or st.session_state.authentication_state:
        st.session_state.authentication_state = True
    if st.session_state.authentication_state:
        set_turboserver(server_address)
        authentication_status = authenticate_user(username, password)
        if ((authentication_status != 200) or (authentication_token == '')):
            login_container.warning("Authentication failed!")
        else:
            login_container.success("Authentication successful")
            if (selected_page == "Metrics"):
                
                data_container = st.container()

                vm_selector_container = data_container.container()
                vms = get_vms_list()
                vmslist = vm_selector_container.selectbox( 'Which VM would you like to display details for?', vms.values())
                (selected_vm_name, selected_vm_uuid) = vmslist.split('#')
                selected_vm_name = selected_vm_name.strip()
                selected_vm_uuid = selected_vm_uuid.strip()
                # data_container.write('You selected:', selected_vm_name)

                metrics_overview_tab, metrics_graphs = data_container.tabs(["Overview", "All metrics"])

                with metrics_overview_tab:
                    tags_container = metrics_overview_tab.container()
                    tags_container.subheader("Tags")
                    tags_container.dataframe(data=get_tags(selected_vm_uuid))

                    actions_container = metrics_overview_tab.container()
                    actions_container.subheader("Actions")
                    actions_container.dataframe(data=get_actions(selected_vm_uuid))

                    metrics_container = metrics_overview_tab.container()
                    metrics_container.subheader("Metrics")
                    timeframe = metrics_container.select_slider('Select the timeframe:', options=['-30d', '-7d', '-3d', '-1d', '-12h', '-2h', '-1h'], value='-1d', key="overview_timeselector")

                    # Compute metrics
                    #print(data_vcpu.transpose().describe())
                    #data_vcpu_percentile = data_vcpu.transpose().quantile(q=0.9)
                    #print(data_vcpu.transpose().quantile(q=0.9))
                    data_vcpu = get_stats(selected_vm_uuid, "VCPU", timeframe)
                    data_vmem = get_stats(selected_vm_uuid, "VMEM", timeframe)
                    compute_vcpu_frame = { 'vCPU': data_vcpu }
                    compute_vmem_frame = { 'vMem': data_vmem }
                    compute_vcpu_frame["VCPU Percentile"] = data_vcpu.transpose().quantile(q=0.9)
                    compute_vmem_frame["VMEM Percentile"] = data_vmem.transpose().quantile(q=0.9)
                    compute_vcpu_df = pd.DataFrame(compute_vcpu_frame)
                    compute_vmem_df = pd.DataFrame(compute_vmem_frame)
                    
                    # Queue metrics
                    data_q1vcpu = get_stats(selected_vm_uuid, "Q1VCPU", timeframe)
                    if len(data_q1vcpu.index) > 0:
                        queue_frame = { 'Q1 vCPU': data_q1vcpu }
                    data_q2vcpu = get_stats(selected_vm_uuid, "Q2VCPU", timeframe)
                    if len(data_q2vcpu.index) > 0:
                        queue_frame = { 'Q2 vCPU': data_q2vcpu }
                    data_q4vcpu = get_stats(selected_vm_uuid, "Q4VCPU", timeframe)
                    if len(data_q4vcpu.index) > 0:
                        queue_frame = { 'Q4 vCPU': data_q4vcpu }
                    data_q8vcpu = get_stats(selected_vm_uuid, "Q8VCPU", timeframe)
                    if len(data_q8vcpu.index) > 0:
                        queue_frame = { 'Q8 vCPU': data_q4vcpu }
                    data_q16vcpu = get_stats(selected_vm_uuid, "Q16VCPU", timeframe)
                    if len(data_q16vcpu.index) > 0:
                        queue_frame = { 'Q16 vCPU': data_q16vcpu }
                    data_q32vcpu = get_stats(selected_vm_uuid, "Q32VCPU", timeframe)
                    if len(data_q32vcpu.index) > 0:
                        queue_frame = { 'Q32 vCPU': data_q32vcpu }
                    data_q64vcpu = get_stats(selected_vm_uuid, "Q64VCPU", timeframe)
                    if len(data_q64vcpu.index) > 0:
                        queue_frame = { 'Q64 vCPU': data_q64vcpu }
                    data_q128vcpu = get_stats(selected_vm_uuid, "Q128VCPU", timeframe)
                    if len(data_q128vcpu.index) > 0:
                        queue_frame = { 'Q128 vCPU': data_q128vcpu }
                    #queue_frame = { 'Q1VCPU': data_q1vcpu, 'Q2VCPU': data_q2vcpu, 'Q4VCPU': data_q4vcpu, 'Q8VCPU': data_q8vcpu, 'Q16VCPU': data_q16vcpu, 'Q32VCPU': data_q32vcpu, 'Q64VCPU': data_q64vcpu, 'Q128VCPU': data_q128vcpu }
                    queue_df = pd.DataFrame(queue_frame)

                    # Storage metrics
                    data_storageaccess = get_stats(selected_vm_uuid, "VStorage", timeframe)
                    data_storagelatency = get_stats(selected_vm_uuid, "StorageLatency", timeframe)
                    storage_frame = { 'Storage Access': data_storageaccess, 'Storage Latency': data_storagelatency }
                    storage_df = pd.DataFrame(storage_frame)
                    
                    col1, col2 = metrics_container.columns(2)
                    #col1.line_chart(compute_vcpu_df)
                    fig_vcpu = px.line(compute_vcpu_df, title="vCPU Utilization", labels={'index': "Date", 'value': "Utilization", 'variable': "Metrics"}, render_mode='auto', range_y=[0,100])
                    fig_vcpu.update_layout(legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ))
                    col1.plotly_chart(fig_vcpu, use_container_width=True, sharing="streamlit")
                    #col2.line_chart(compute_vmem_df)
                    fig_vmem = px.line(compute_vmem_df, title="vMem Utilization", labels={'index': "Date", 'value': "Utilization", 'variable': "Metrics"}, render_mode='auto', range_y=[0,100])
                    fig_vmem.update_layout(legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ))
                    col2.plotly_chart(fig_vmem, use_container_width=True, sharing="streamlit")
                    #col1.line_chart(queue_df)
                    fig_queue = px.line(queue_df, title="Queue Utilization", labels={'index': "Date", 'value': "Utilization", 'variable': "Metrics"}, render_mode='auto', range_y=[0,100])
                    fig_queue.update_layout(legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ))
                    col1.plotly_chart(fig_queue, use_container_width=True, sharing="streamlit")
                    #col2.line_chart(storage_df)
                    fig_storage = px.line(storage_df, title="Storage Utilization", labels={'index': "Date", 'value': "Utilization", 'variable': "Metrics"}, render_mode='auto', range_y=[0,100])
                    fig_storage.update_layout(legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ))
                    col2.plotly_chart(fig_storage, use_container_width=True, sharing="streamlit")

                with metrics_graphs:
                    metrics_graphs_container = metrics_graphs.container()
                    metrics_graphs_container.subheader("Metrics Graphs")

                    metrics_timeframe = metrics_graphs_container.select_slider('Select the timeframe:', options=['-30d', '-7d', '-3d', '-1d', '-12h', '-2h', '-1h'], value='-1d', key="metrics_graphs_timeselector")
                    
                    metrics_selector = metrics_graphs_container.multiselect('What metrics do you want to graph?', get_stats_list(selected_vm_uuid))
                    #print(metrics_selector)
                    frame = {}
                    for metric in metrics_selector:
                        data = get_stats(selected_vm_uuid, metric, metrics_timeframe)
                        frame[metric] = data
                    current_df = pd.DataFrame.from_dict(frame)
                    #metrics_graphs_container.line_chart(current_df)
                    fig_metric = px.line(current_df, title="Utilization", labels={'index': "Date", 'value': "Utilization", 'variable': "Metrics"}, render_mode='auto', range_y=[0,100])
                    metrics_graphs_container.plotly_chart(fig_metric, use_container_width=True, sharing="streamlit")


            elif (selected_page == "Policies"):
                policies_container = st.container()
                policies_container.subheader("List of placement policies")
                policies_container.dataframe(data=get_placement_policies())
                policies_container.subheader("List of automation policies")
                selected_policies = policies_container.selectbox("PolicyFilter", ["User Created Only", "Default Only", "All"])
                all_policies = get_automation_policies()
                default_policies = all_policies.loc[(all_policies['is_default'] == True)]
                user_policies = all_policies.loc[(all_policies['is_default'] == False) & (all_policies['is_readonly'] == False)]
                #print(user_policies)
                #print(user_policies))
                #print(user_policies.shape())
                if selected_policies == "All":
                    policies_container.dataframe(data=all_policies)
                elif selected_policies == "Default Only":
                    policies_container.dataframe(data=default_policies)
                else:
                    policies_container.dataframe(data=user_policies)
                    #fig_user_policies = ff.create_table(user_policies)
                    #policies_container.plotly_chart(fig_user_policies, use_container_width=True, sharing="streamlit")

if __name__ == '__main__':
    main()
