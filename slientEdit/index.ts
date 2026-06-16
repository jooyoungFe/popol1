import { definePluginSettings } from "@api/Settings";
import definePlugin, { OptionType, PluginAuthor } from "@utils/types";
import { Constants, RestAPI, UserStore, MessageStore } from "@webpack/common";
import { findByPropsLazy } from "@webpack";

declare const WebpackModules: any;
declare const React: any;

const MessageActions = findByPropsLazy("deleteMessage", "startEditMessage", "editMessage");

const settings = definePluginSettings({
    enabled: {
        type: OptionType.BOOLEAN,
        default: true,
        description: "wanna turn this lil plugin on or off?"
    },
    deleteOriginalMessage: {
        type: OptionType.BOOLEAN,
        default: true,
        description: "poof! deletes the original message after a sneaky edit. if it's off, your old message might pop back up after a reload, oops!",
    },
    deleteDelay: {
        type: OptionType.NUMBER,
        default: 500,
        description: "how long (in milliseconds) to wait before making that old message poof.",
    },
    suppressNotifications: {
        type: OptionType.BOOLEAN,
        default: false,
        description: "super recommended for dms so you don't accidentally poke your friends with a ping!",
    }
});

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

function sendMessageToDiscord(content: string, nonce: string, channelId: string, suppressNotifications: boolean, messageReference?: any) {
    const body: any = {
        content,
        flags: suppressNotifications ? 4096 : 0,
        mobile_network_type: "unknown",
        nonce,
        tts: false,
    };

    if (messageReference) {
        body.message_reference = {
            channel_id: messageReference.channel_id,
            message_id: messageReference.message_id,
            guild_id: messageReference.guild_id
        };
    }

    return RestAPI.post({
        url: Constants.Endpoints.MESSAGES(channelId),
        body
    });
}

function deleteMessageFromDiscord(channelId: string, messageId: string) {
    return RestAPI.del({
        url: Constants.Endpoints.MESSAGE(channelId, messageId)
    });
}

export default definePlugin({
    name: "NoEditMark",
    description: "no more 'edited' tags when you tweak your messages, yay!",
    authors: [{ name: "jooyoung", id: 1022487323465744477n } as PluginAuthor],
    dependencies: [],
    settings,

    _originalEditMessage: undefined as ((channelId: string, messageId: string, content: any) => Promise<any>) | undefined,

    start(this: any) {
        console.log("[NoEditMark] plugin started! gonna sneakily hook messageactions.editmessage.");

        if (!MessageActions || !MessageActions.editMessage) {
            console.error("[NoEditMark] oopsie! couldn't find messageactions.editmessage. plugin might not work, boo!");
            return;
        }

        this._originalEditMessage = MessageActions.editMessage;

        MessageActions.editMessage = async (channelId: string, messageId: string, content: any) => {
            if (!(settings.store as any).enabled) {
                return this._originalEditMessage!.apply(MessageActions, [channelId, messageId, content]);
            }

            const currentUser = UserStore.getCurrentUser();
            const newContent = typeof content === 'string' ? content : content.content;
            const messageObj = MessageStore.getMessage(channelId, messageId);

            if (!messageObj || messageObj.author.id !== currentUser.id) {
                return this._originalEditMessage!.apply(MessageActions, [channelId, messageId, content]);
            }

            try {
                await sendMessageToDiscord(
                    newContent,
                    messageObj.id,
                    channelId,
                    (settings.store as any).suppressNotifications,
                    messageObj.messageReference
                );
                console.log("[NoEditMark] yay! new message sent with the original nonce, so sneaky.");

                if ((settings.store as any).deleteOriginalMessage) {
                    await sleep((settings.store as any).deleteDelay);
                    await deleteMessageFromDiscord(channelId, messageId);
                    console.log("[NoEditMark] old message poofed away!");
                }
            } catch (error) {
                console.error("[NoEditMark] uh oh! something went wrong during the sneaky edit:", error);
                return this._originalEditMessage!.apply(MessageActions, [channelId, messageId, content]);
            }
        };
    },

    stop(this: any) {
        console.log("[NoEditMark] plugin stopped. bringing back the original messageactions.editmessage.");
        if (this._originalEditMessage) {
            MessageActions.editMessage = this._originalEditMessage;
            this._originalEditMessage = undefined;
        }
    },

    getSettingsPanel(this: any): React.ReactElement {
        const SwitchItemModule = WebpackModules.findByProps("SwitchItem");
        const SwitchItem = SwitchItemModule ? SwitchItemModule.SwitchItem : null;
        const NumberInput = WebpackModules.findByProps("NumberInput")?.NumberInput;
        const TextInput = WebpackModules.findByProps("TextInput")?.TextInput;

        if (!SwitchItem || !NumberInput || !TextInput) {
            return React.createElement("div", null, "oopsie! couldn't load the stuff needed for settings, sorry!");
        }

        return React.createElement(
            "div",
            null,
            React.createElement(
                SwitchItem,
                {
                    value: (settings.store as any).enabled,
                    onChange: (value: boolean) => {
                        (settings.store as any).enabled = value;
                    },
                    note: "wanna turn this lil plugin on or off?"
                },
                "Enable Plugin"
            ),
            React.createElement(
                SwitchItem,
                {
                    value: (settings.store as any).deleteOriginalMessage,
                    onChange: (value: boolean) => {
                        (settings.store as any).deleteOriginalMessage = value;
                    },
                    note: "poof! deletes the original message after a sneaky edit. if it's off, your old message might pop back up after a reload, oops!"
                },
                "Delete Original Message"
            ),
            React.createElement(
                NumberInput,
                {
                    value: (settings.store as any).deleteDelay,
                    onChange: (value: number) => {
                        (settings.store as any).deleteDelay = value;
                    },
                    min: 0,
                    max: 5000,
                    step: 100,
                    title: "Delete Delay (ms)",
                    note: "how long (in milliseconds) to wait before making that old message poof."
                }
            ),
            React.createElement(
                SwitchItem,
                {
                    value: (settings.store as any).suppressNotifications,
                    onChange: (value: boolean) => {
                        (settings.store as any).suppressNotifications = value;
                    },
                    note: "super recommended for dms so you don't accidentally poke your friends with a ping!"
                },
                "Suppress Notifications"
            )
        );
    }
});