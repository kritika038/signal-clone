with open("frontend/features/chat/components/signal-shell.tsx", "r") as f:
    content = f.read()

# 1. Add import
old_import_contacts = "import { NewContactModal } from \"./new-contact-modal\";"
new_import = "import { NewContactModal } from \"./new-contact-modal\";\nimport { ConversationInfoModal } from \"./conversation-info-modal\";"
content = content.replace(old_import_contacts, new_import)

# 2. Add state
old_state = "  const [showNewContact, setShowNewContact] = useState(false);"
new_state = "  const [showNewContact, setShowNewContact] = useState(false);\n  const [showConversationInfo, setShowConversationInfo] = useState(false);"
content = content.replace(old_state, new_state)

# 3. Replace gear icon action
old_gear = """                <ToolbarIcon label="Conversation Info" onClick={() => openSettings("about")}>
                  <Settings className="h-4 w-4" />
                </ToolbarIcon>"""
new_gear = """                <ToolbarIcon label="Conversation Info" onClick={() => setShowConversationInfo(true)}>
                  <Settings className="h-4 w-4" />
                </ToolbarIcon>"""
content = content.replace(old_gear, new_gear)

# 4. Render ConversationInfoModal
old_modals = """      <CreateGroupModal isOpen={showNewGroup} onClose={() => setShowNewGroup(false)} />
      <NewContactModal isOpen={showNewContact} onClose={() => setShowNewContact(false)} />"""
new_modals = """      <CreateGroupModal isOpen={showNewGroup} onClose={() => setShowNewGroup(false)} />
      <NewContactModal isOpen={showNewContact} onClose={() => setShowNewContact(false)} />
      <ConversationInfoModal isOpen={showConversationInfo} onClose={() => setShowConversationInfo(false)} />"""
content = content.replace(old_modals, new_modals)

with open("frontend/features/chat/components/signal-shell.tsx", "w") as f:
    f.write(content)
print("Updated signal-shell.tsx with ConversationInfoModal")
