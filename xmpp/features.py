##   features.py 
##
##   Copyright (C) 2003 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id$

from protocol import *

############### Namespaces that jabberd2 reports ################
NS_AGENTS='jabber:iq:agents'
NS_DATA='jabber:x:data'
NS_DISCO='http://jabber.org/protocol/disco'
NS_INVISIBLE='presence-invisible'
NS_IQ='iq'
NS_LAST='jabber:iq:last'
NS_MESSAGE='message'
NS_PRESENCE='presence'
NS_PRIVACY='jabber:iq:privacy'
NS_PRIVATE='jabber:iq:private'
NS_REGISTER='jabber:iq:register'
NS_ROSTER='jabber:iq:roster'
NS_TIME='jabber:iq:time'
NS_VACATION='http://jabber.org/protocol/vacation'
NS_VCARD='vcard-temp'
NS_VERSION='jabber:iq:version'

NS_BROWSE='jabber:iq:browse'
NS_DISCO_ITEMS=NS_DISCO+'#items'
NS_DISCO_INFO=NS_DISCO+'#info'
NS_GROUPCHAT='gc-1.0'
NS_SEARCH='jabber:iq:search'

### DISCO ### http://jabber.org/protocol/disco ### JEP-0030 ####################
### Browse ### jabber:iq:browse ### JEP-0030 ###################################
### Agents ### jabber:iq:agents ### JEP-0030 ###################################
def _discover(disp,ns,jid,node=None,fb2b=0,fb2a=1):
    iq=Iq(to=jid,type='get',queryNS=ns)
    if node: iq.setAttr('node',node)
    rep=disp.SendAndWaitForResponse(iq)
    if fb2b and errorNode(rep): rep=disp.SendAndWaitForResponse(Iq(to=jid,type='get',queryNS=NS_BROWSE))   # Fallback to browse
    if fb2a and errorNode(rep): rep=disp.SendAndWaitForResponse(Iq(to=jid,type='get',queryNS=NS_AGENTS))   # Fallback to agents
    if resultNode(rep): return rep.getQueryPayload()
    return []

def discoverItems(disp,jid,node=None):
    """ According to JEP-0030:
        query MAY have node attribute
        item: MUST HAVE jid attribute and MAY HAVE name, node, action attributes.
        action attribute of item can be either of remove or update value."""
    ret=[]
    for i in _discover(disp,NS_DISCO_ITEMS,jid,node):
        if i.getName()=='agent' and i.getTag('name'): i.setAttr('name',i.getTagData('name'))
        ret.append(i.attrs)
    return ret

def discoverInfo(disp,jid,node=None):
    """ According to JEP-0030:
        query MAY have node attribute
        identity: MUST HAVE category and name attributes and MAY HAVE type attribute.
        feature: MUST HAVE var attribute"""
    identities , features = [] , []
    for i in _discover(disp,NS_DISCO_INFO,jid,node):
        if i.getName()=='identity': identities.append(i.attrs)
        elif i.getName()=='feature': features.append(i.getAttr('var'))
        elif i.getName()=='agent':
            if i.getTag('name'): i.setAttr('name',i.getTagData('name'))
            if i.getTag('description'): i.setAttr('name',i.getTagData('description'))
            identities.append(i.attrs)
            if i.getTag('groupchat'): features.append(NS_GROUPCHAT)
            if i.getTag('register'): features.append(NS_REGISTER)
            if i.getTag('search'): features.append(NS_SEARCH)
    return identities , features

### Registration ### jabber:iq:register ### JEP-0077 ###########################
def getRegInfo(disp,jid,info={}):
    iq=Iq('get',NS_REGISTER,to=jid)
    for i in info.keys(): iq.setTagData(i,info[i])
    resp=disp.SendAndWaitForResponse(iq)
    if not resultNode(rep): return
    df=resp.getTag('query',namespace=NS_REGISTER).getTag('x',namespace=NS_DATA)
    if df: return DataForm(node=df)
    df=DataForm(NS_DATA+' x',{'type':'form'})
    for i in resp.getQueryPayload():
        if i.getName()=='instructions': df.addChild(node=i)
        else: df.addChild(node=Node('field',{'var':i.getName(),'type':'text-single'},payload=[Node('value',payload=[i.getData()])]))
    return df

def register(disp,jid,info):
    iq=Iq('set',NS_REGISTER,to=jid)
    if type(info)<>type({}): info=info.asDict()
    for i in info.keys(): iq.setTag('query').setTagData(i,info[i])
    resp=disp.SendAndWaitForResponse(iq)
    if resultNode(resp): return 1

def unregister(disp,jid):
    resp=disp.SendAndWaitForResponse(Iq('set',NS_REGISTER,to=jid,payload=[Node('remove')]))
    if resultNode(resp): return 1

def changePasswordTo(disp,newpassword):
    resp=disp.SendAndWaitForResponse(Iq('set',NS_REGISTER,to=disp._owner.Server,payload=[Node('username',payload=[disp._owner.Server]),Node('password',payload=[newpassword])]))
    if resultNode(resp): return 1

### Privacy ### jabber:iq:privacy ### draft-ietf-xmpp-im-19 ####################

def getPrivacyLists(disp):
    try:
        dict={'lists':[]}
        resp=disp.SendAndWaitForResponse(Iq('get',NS_PRIVACY))
        if not resultNode(resp): return
        for list in resp.getQueryPayload():
            if list.getName()=='list': dict['lists'].append(list.getAttr('name'))
            else: dict[list.getName()]=list.getAttr('name')
        return dict
    except: pass

def getPrivacyList(disp,listname):
    try:
        resp=disp.SendAndWaitForResponse(Iq('get',NS_PRIVACY,payload=[Node('list',{'name':listname})]))
        if resultNode(resp): return resp.getQueryPayload()[0].getTag('list',{'name':listname})
    except: pass

def setActivePrivacyList(disp,listname=None,type='active'):
    if listname: attrs={'name':listname}
    else: attrs=None
    resp=disp.SendAndWaitForResponse(Iq('set',NS_PRIVACY,payload=[Node(type,attrs)]))
    if resultNode(resp): return 1

def setActivePrivacyList(disp,listname=None): return SetActivePrivacyList(disp,listname,'default')

def setPrivacyList(disp,payload):
    resp=disp.SendAndWaitForResponse(Iq('set',NS_PRIVACY,payload=[payload]))
    if resultNode(resp): return 1

def delPrivacyList(disp,listname):
    resp=disp.SendAndWaitForResponse(Iq('set',NS_PRIVACY,payload=[Node('list',{'name':listname})]))
    if resultNode(resp): return 1