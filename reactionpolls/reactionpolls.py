"""
MIT License

Copyright (c) 2021-present Obi-Wan3

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import re
import typing

import discord
from redbot.core import commands, Config

NUMBER_REACTIONS = [
    "\N{DIGIT ZERO}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT ONE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT TWO}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT THREE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT FOUR}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT FIVE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT SIX}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT SEVEN}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT EIGHT}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT NINE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{KEYCAP TEN}",
    "\N{PERMANENT PAPER SIGN}\N{VARIATION SELECTOR-16}"
]

LETTER_REACTIONS = {
    "a": "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
    "b": "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
    "c": "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
    "d": "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
    "e": "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
    "f": "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
    "g": "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
    "h": "\N{REGIONAL INDICATOR SYMBOL LETTER H}",
    "i": "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
    "j": "\N{REGIONAL INDICATOR SYMBOL LETTER J}",
    "k": "\N{REGIONAL INDICATOR SYMBOL LETTER K}",
    "l": "\N{REGIONAL INDICATOR SYMBOL LETTER L}",
    "m": "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
    "n": "\N{REGIONAL INDICATOR SYMBOL LETTER N}",
    "o": "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
    "p": "\N{REGIONAL INDICATOR SYMBOL LETTER P}",
    "q": "\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
    "r": "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
    "s": "\N{REGIONAL INDICATOR SYMBOL LETTER S}",
    "t": "\N{REGIONAL INDICATOR SYMBOL LETTER T}",
    "u": "\N{REGIONAL INDICATOR SYMBOL LETTER U}",
    "v": "\N{REGIONAL INDICATOR SYMBOL LETTER V}",
    "w": "\N{REGIONAL INDICATOR SYMBOL LETTER W}",
    "x": "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "y": "\N{REGIONAL INDICATOR SYMBOL LETTER Y}",
    "z": "\N{REGIONAL INDICATOR SYMBOL LETTER Z}"
}

# Fetched from Discord inspect element sources & processed with https://github.com/Obi-Wan3/Discord-Emojis
EMOJI_LIST = ['😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣', '☺️', '😊', '😇', '🙂', '🙃', '😉', '😌', '🥲', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😝', '😜', '🤪', '🤨', '🧐', '🤓', '😎', '🤩', '🥳', '😏', '😒', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖', '😫', '😩', '🥺', '😢', '😭', '😤', '😠', '😡', '🤬', '🤯', '😳', '🥵', '🥶', '😱', '😨', '😰', '😥', '😓', '🤗', '🤔', '🤭', '🥱', '🤫', '🤥', '😶', '😐', '😑', '😬', '🙄', '😯', '😦', '😧', '😮', '😲', '😴', '🤤', '😪', '😵', '🤐', '🥴', '🤢', '🤮', '🤧', '😷', '🤒', '🤕', '🤑', '🤠', '🥸', '😈', '👿', '👹', '👺', '🤡', '💩', '👻', '💀', '☠️', '👽', '👾', '🤖', '🎃', '😺', '😸', '😹', '😻', '😼', '😽', '🙀', '😿', '😾', '🤲', '👐', '🙌', '👏', '🤝', '👍', '👎', '👊', '✊', '🤛', '🤜', '🤞', '✌️', '🤟', '🤘', '👌', '🤏', '🤌', '👈', '👉', '👆', '👇', '☝️', '✋', '🤚', '🖐️', '🖖', '👋', '🤙', '💪', '🦾', '🖕', '✍️', '🙏', '🦶', '🦵', '🦿', '💄', '💋', '👄', '🦷', '🦴', '👅', '👂', '🦻', '👃', '👣', '👁️', '👀', '🧠', '🫀', '🫁', '🗣️', '👤', '👥', '🫂', '👶', '👧', '🧒', '👦', '👩', '🧑', '👨', '🧑\u200d🦱', '👩\u200d🦱', '👨\u200d🦱', '🧑\u200d🦰', '👩\u200d🦰', '👨\u200d🦰', '👱\u200d♀️', '👱', '👱\u200d♂️', '🧑\u200d🦳', '👩\u200d🦳', '👨\u200d🦳', '🧑\u200d🦲', '👩\u200d🦲', '👨\u200d🦲', '🧔', '👵', '🧓', '👴', '👲', '👳', '👳\u200d♀️', '👳\u200d♂️', '🧕', '👮', '👮\u200d♀️', '👮\u200d♂️', '👷', '👷\u200d♀️', '👷\u200d♂️', '💂', '💂\u200d♀️', '💂\u200d♂️', '🕵️', '🕵️\u200d♀️', '🕵️\u200d♂️', '🧑\u200d⚕️', '👩\u200d⚕️', '👨\u200d⚕️', '🧑\u200d🌾', '👩\u200d🌾', '👨\u200d🌾', '🧑\u200d🍳', '👩\u200d🍳', '👨\u200d🍳', '🧑\u200d🎓', '👩\u200d🎓', '👨\u200d🎓', '🧑\u200d🎤', '👩\u200d🎤', '👨\u200d🎤', '🧑\u200d🏫', '👩\u200d🏫', '👨\u200d🏫', '🧑\u200d🏭', '👩\u200d🏭', '👨\u200d🏭', '🧑\u200d💻', '👩\u200d💻', '👨\u200d💻', '🧑\u200d💼', '👩\u200d💼', '👨\u200d💼', '🧑\u200d🔧', '👩\u200d🔧', '👨\u200d🔧', '🧑\u200d🔬', '👩\u200d🔬', '👨\u200d🔬', '🧑\u200d🎨', '👩\u200d🎨', '👨\u200d🎨', '🧑\u200d🚒', '👩\u200d🚒', '👨\u200d🚒', '🧑\u200d✈️', '👩\u200d✈️', '👨\u200d✈️', '🧑\u200d🚀', '👩\u200d🚀', '👨\u200d🚀', '🧑\u200d⚖️', '👩\u200d⚖️', '👨\u200d⚖️', '👰', '👰\u200d♀️', '👰\u200d♂️', '🤵', '🤵\u200d♀️', '🤵\u200d♂️', '👸', '🤴', '🦸', '🦸\u200d♀️', '🦸\u200d♂️', '🦹', '🦹\u200d♀️', '🦹\u200d♂️', '🥷', '🧑\u200d🎄', '🤶', '🎅', '🧙', '🧙\u200d♀️', '🧙\u200d♂️', '🧝', '🧝\u200d♀️', '🧝\u200d♂️', '🧛', '🧛\u200d♀️', '🧛\u200d♂️', '🧟', '🧟\u200d♀️', '🧟\u200d♂️', '🧞', '🧞\u200d♀️', '🧞\u200d♂️', '🧜', '🧜\u200d♀️', '🧜\u200d♂️', '🧚', '🧚\u200d♀️', '🧚\u200d♂️', '👼', '🤰', '🤱', '🧑\u200d🍼', '👩\u200d🍼', '👨\u200d🍼', '🙇', '🙇\u200d♀️', '🙇\u200d♂️', '💁', '💁\u200d♀️', '💁\u200d♂️', '🙅', '🙅\u200d♀️', '🙅\u200d♂️', '🙆', '🙆\u200d♀️', '🙆\u200d♂️', '🙋', '🙋\u200d♀️', '🙋\u200d♂️', '🧏', '🧏\u200d♀️', '🧏\u200d♂️', '🤦', '🤦\u200d♀️', '🤦\u200d♂️', '🤷', '🤷\u200d♀️', '🤷\u200d♂️', '🙎', '🙎\u200d♀️', '🙎\u200d♂️', '🙍', '🙍\u200d♀️', '🙍\u200d♂️', '💇', '💇\u200d♀️', '💇\u200d♂️', '💆', '💆\u200d♀️', '💆\u200d♂️', '🧖', '🧖\u200d♀️', '🧖\u200d♂️', '💅', '🤳', '💃', '🕺', '👯', '👯\u200d♀️', '👯\u200d♂️', '🕴️', '🧑\u200d🦽', '👩\u200d🦽', '👨\u200d🦽', '🧑\u200d🦼', '👩\u200d🦼', '👨\u200d🦼', '🚶', '🚶\u200d♀️', '🚶\u200d♂️', '🧑\u200d🦯', '👩\u200d🦯', '👨\u200d🦯', '🧎', '🧎\u200d♀️', '🧎\u200d♂️', '🏃', '🏃\u200d♀️', '🏃\u200d♂️', '🧍', '🧍\u200d♀️', '🧍\u200d♂️', '🧑\u200d🤝\u200d🧑', '👫', '👭', '👬', '💑', '👩\u200d❤️\u200d👨', '👩\u200d❤️\u200d👩', '👨\u200d❤️\u200d👨', '💏', '👩\u200d❤️\u200d💋\u200d👨', '👩\u200d❤️\u200d💋\u200d👩', '👨\u200d❤️\u200d💋\u200d👨', '👪', '👨\u200d👩\u200d👦', '👨\u200d👩\u200d👧', '👨\u200d👩\u200d👧\u200d👦', '👨\u200d👩\u200d👦\u200d👦', '👨\u200d👩\u200d👧\u200d👧', '👩\u200d👩\u200d👦', '👩\u200d👩\u200d👧', '👩\u200d👩\u200d👧\u200d👦', '👩\u200d👩\u200d👦\u200d👦', '👩\u200d👩\u200d👧\u200d👧', '👨\u200d👨\u200d👦', '👨\u200d👨\u200d👧', '👨\u200d👨\u200d👧\u200d👦', '👨\u200d👨\u200d👦\u200d👦', '👨\u200d👨\u200d👧\u200d👧', '👩\u200d👦', '👩\u200d👧', '👩\u200d👧\u200d👦', '👩\u200d👦\u200d👦', '👩\u200d👧\u200d👧', '👨\u200d👦', '👨\u200d👧', '👨\u200d👧\u200d👦', '👨\u200d👦\u200d👦', '👨\u200d👧\u200d👧', '🧶', '🧵', '🧥', '🥼', '🦺', '👚', '👕', '👖', '🩲', '🩳', '👔', '👗', '👙', '🩱', '👘', '🥻', '🥿', '👠', '👡', '👢', '👞', '👟', '🥾', '🩴', '🧦', '🧤', '🧣', '🎩', '🧢', '👒', '🎓', '⛑️', '🪖', '👑', '💍', '👝', '👛', '👜', '💼', '🎒', '🧳', '👓', '🕶️', '🥽', '🌂', '🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐻\u200d❄️', '🐨', '🐯', '🦁', '🐮', '🐷', '🐽', '🐸', '🐵', '🙈', '🙉', '🙊', '🐒', '🐔', '🐧', '🐦', '🐤', '🐣', '🐥', '🦆', '🦤', '🦅', '🦉', '🦇', '🐺', '🐗', '🐴', '🦄', '🐝', '🐛', '🦋', '🐌', '🪱', '🐞', '🐜', '🪰', '🦟', '🪳', '🪲', '🦗', '🕷️', '🕸️', '🦂', '🐢', '🐍', '🦎', '🦖', '🦕', '🐙', '🦑', '🦐', '🦞', '🦀', '🐡', '🐠', '🐟', '🦭', '🐬', '🐳', '🐋', '🦈', '🐊', '🐅', '🐆', '🦓', '🦍', '🦧', '🐘', '🦣', '🦬', '🦛', '🦏', '🐪', '🐫', '🦒', '🦘', '🐃', '🐂', '🐄', '🐎', '🐖', '🐏', '🐑', '🦙', '🐐', '🦌', '🐕', '🐩', '🦮', '🐕\u200d🦺', '🐈', '🐈\u200d⬛', '🐓', '🦃', '🦚', '🦜', '🦢', '🦩', '🕊️', '🐇', '🦝', '🦨', '🦡', '🦫', '🦦', '🦥', '🐁', '🐀', '🐿️', '🦔', '🐾', '🐉', '🐲', '🌵', '🎄', '🌲', '🌳', '🌴', '🌱', '🌿', '☘️', '🍀', '🎍', '🎋', '🍃', '🍂', '🍁', '🪶', '🍄', '🐚', '🪨', '🪵', '🌾', '🪴', '💐', '🌷', '🌹', '🥀', '🌺', '🌸', '🌼', '🌻', '🌞', '🌝', '🌛', '🌜', '🌚', '🌕', '🌖', '🌗', '🌘', '🌑', '🌒', '🌓', '🌔', '🌙', '🌎', '🌍', '🌏', '🪐', '💫', '⭐', '🌟', '✨', '⚡', '☄️', '💥', '🔥', '🌪️', '🌈', '☀️', '🌤️', '⛅', '🌥️', '☁️', '🌦️', '🌧️', '⛈️', '🌩️', '🌨️', '❄️', '☃️', '⛄', '🌬️', '💨', '💧', '💦', '☔', '☂️', '🌊', '🌫️', '🍏', '🍎', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🫐', '🍓', '🍈', '🍒', '🍑', '🥭', '🍍', '🥥', '🥝', '🍅', '🍆', '🥑', '🫒', '🥦', '🥬', '🫑', '🥒', '🌶️', '🌽', '🥕', '🧄', '🧅', '🥔', '🍠', '🥐', '🥯', '🍞', '🥖', '🫓', '🥨', '🧀', '🥚', '🍳', '🧈', '🥞', '🧇', '🥓', '🥩', '🍗', '🍖', '🌭', '🍔', '🍟', '🍕', '🥪', '🥙', '🧆', '🌮', '🌯', '🫔', '🥗', '🥘', '🫕', '🥫', '🍝', '🍜', '🍲', '🍛', '🍣', '🍱', '🥟', '🦪', '🍤', '🍙', '🍚', '🍘', '🍥', '🥠', '🥮', '🍢', '🍡', '🍧', '🍨', '🍦', '🥧', '🧁', '🍰', '🎂', '🍮', '🍭', '🍬', '🍫', '🍿', '🍩', '🍪', '🌰', '🥜', '🍯', '🥛', '🍼', '☕', '🍵', '🫖', '🧉', '🧋', '🧃', '🥤', '🍶', '🍺', '🍻', '🥂', '🍷', '🥃', '🍸', '🍹', '🍾', '🧊', '🥄', '🍴', '🍽️', '🥣', '🥡', '🥢', '🧂', '⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🥏', '🪃', '🎱', '🪀', '🏓', '🏸', '🏒', '🏑', '🥍', '🏏', '🥅', '⛳', '🪁', '🏹', '🎣', '🤿', '🥊', '🥋', '🎽', '🛹', '🛼', '🛷', '⛸️', '🥌', '🎿', '⛷️', '🏂', '🪂', '🏋️', '🏋️\u200d♀️', '🏋️\u200d♂️', '🤼', '🤼\u200d♀️', '🤼\u200d♂️', '🤸', '🤸\u200d♀️', '🤸\u200d♂️', '⛹️', '⛹️\u200d♀️', '⛹️\u200d♂️', '🤺', '🤾', '🤾\u200d♀️', '🤾\u200d♂️', '🏌️', '🏌️\u200d♀️', '🏌️\u200d♂️', '🏇', '🧘', '🧘\u200d♀️', '🧘\u200d♂️', '🏄', '🏄\u200d♀️', '🏄\u200d♂️', '🏊', '🏊\u200d♀️', '🏊\u200d♂️', '🤽', '🤽\u200d♀️', '🤽\u200d♂️', '🚣', '🚣\u200d♀️', '🚣\u200d♂️', '🧗', '🧗\u200d♀️', '🧗\u200d♂️', '🚵', '🚵\u200d♀️', '🚵\u200d♂️', '🚴', '🚴\u200d♀️', '🚴\u200d♂️', '🏆', '🥇', '🥈', '🥉', '🏅', '🎖️', '🏵️', '🎗️', '🎫', '🎟️', '🎪', '🤹', '🤹\u200d♀️', '🤹\u200d♂️', '🎭', '🩰', '🎨', '🎬', '🎤', '🎧', '🎼', '🎹', '🥁', '🪘', '🎷', '🎺', '🎸', '🪕', '🎻', '🪗', '🎲', '♟️', '🎯', '🎳', '🎮', '🎰', '🧩', '🚗', '🚕', '🚙', '🛻', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒', '🚐', '🚚', '🚛', '🚜', '🦯', '🦽', '🦼', '🛴', '🚲', '🛵', '🏍️', '🛺', '🚨', '🚔', '🚍', '🚘', '🚖', '🚡', '🚠', '🚟', '🚃', '🚋', '🚞', '🚝', '🚄', '🚅', '🚈', '🚂', '🚆', '🚇', '🚊', '🚉', '✈️', '🛫', '🛬', '🛩️', '💺', '🛰️', '🚀', '🛸', '🚁', '🛶', '⛵', '🚤', '🛥️', '🛳️', '⛴️', '🚢', '⚓', '⛽', '🚧', '🚦', '🚥', '🚏', '🗺️', '🗿', '🗽', '🗼', '🏰', '🏯', '🏟️', '🎡', '🎢', '🎠', '⛲', '⛱️', '🏖️', '🏝️', '🏜️', '🌋', '⛰️', '🏔️', '🗻', '🏕️', '⛺', '🏠', '🏡', '🏘️', '🏚️', '🛖', '🏗️', '🏭', '🏢', '🏬', '🏣', '🏤', '🏥', '🏦', '🏨', '🏪', '🏫', '🏩', '💒', '🏛️', '⛪', '🕌', '🕍', '🛕', '🕋', '⛩️', '🛤️', '🛣️', '🗾', '🎑', '🏞️', '🌅', '🌄', '🌠', '🎇', '🎆', '🌇', '🌆', '🏙️', '🌃', '🌌', '🌉', '🌁', '⌚', '📱', '📲', '💻', '⌨️', '🖥️', '🖨️', '🖱️', '🖲️', '🕹️', '🗜️', '💽', '💾', '💿', '📀', '📼', '📷', '📸', '📹', '🎥', '📽️', '🎞️', '📞', '☎️', '📟', '📠', '📺', '📻', '🎙️', '🎚️', '🎛️', '🧭', '⏱️', '⏲️', '⏰', '🕰️', '⌛', '⏳', '📡', '🔋', '🔌', '💡', '🔦', '🕯️', '🪔', '🧯', '🛢️', '💸', '💵', '💴', '💶', '💷', '🪙', '💰', '💳', '💎', '⚖️', '🪜', '🧰', '🪛', '🔧', '🔨', '⚒️', '🛠️', '⛏️', '🔩', '⚙️', '🧱', '⛓️', '🪝', '🪢', '🧲', '🔫', '💣', '🧨', '🪓', '🪚', '🔪', '🗡️', '⚔️', '🛡️', '🚬', '⚰️', '🪦', '⚱️', '🏺', '🪄', '🔮', '📿', '🧿', '💈', '⚗️', '🔭', '🔬', '🕳️', '🪟', '🩹', '🩺', '💊', '💉', '🩸', '🧬', '🦠', '🧫', '🧪', '🌡️', '🪤', '🧹', '🧺', '🪡', '🧻', '🚽', '🪠', '🪣', '🚰', '🚿', '🛁', '🛀', '🪥', '🧼', '🪒', '🧽', '🧴', '🛎️', '🔑', '🗝️', '🚪', '🪑', '🪞', '🛋️', '🛏️', '🛌', '🧸', '🖼️', '🛍️', '🛒', '🎁', '🎈', '🎏', '🎀', '🎊', '🎉', '🪅', '🪆', '🎎', '🏮', '🎐', '🧧', '✉️', '📩', '📨', '📧', '💌', '📥', '📤', '📦', '🏷️', '📪', '📫', '📬', '📭', '📮', '📯', '🪧', '📜', '📃', '📄', '📑', '🧾', '📊', '📈', '📉', '🗒️', '🗓️', '📆', '📅', '🗑️', '📇', '🗃️', '🗳️', '🗄️', '📋', '📁', '📂', '🗂️', '🗞️', '📰', '📓', '📔', '📒', '📕', '📗', '📘', '📙', '📚', '📖', '🔖', '🧷', '🔗', '📎', '🖇️', '📐', '📏', '🧮', '📌', '📍', '✂️', '🖊️', '🖋️', '✒️', '🖌️', '🖍️', '📝', '✏️', '🔍', '🔎', '🔏', '🔐', '🔒', '🔓', '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤎', '🤍', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '💟', '☮️', '✝️', '☪️', '🕉️', '☸️', '✡️', '🔯', '🕎', '☯️', '☦️', '🛐', '⛎', '♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓', '🆔', '⚛️', '🉑', '☢️', '☣️', '📴', '📳', '🈶', '🈚', '🈸', '🈺', '🈷️', '✴️', '🆚', '💮', '🉐', '㊙️', '㊗️', '🈴', '🈵', '🈹', '🈲', '🅰️', '🅱️', '🆎', '🆑', '🅾️', '🆘', '❌', '⭕', '🛑', '⛔', '📛', '🚫', '💯', '💢', '♨️', '🚷', '🚯', '🚳', '🚱', '🔞', '📵', '🚭', '❗', '❕', '❓', '❔', '‼️', '⁉️', '🔅', '🔆', '〽️', '⚠️', '🚸', '🔱', '⚜️', '🔰', '♻️', '✅', '🈯', '💹', '❇️', '✳️', '❎', '🌐', '💠', 'Ⓜ️', '🌀', '💤', '🏧', '🚾', '♿', '🅿️', '🈳', '🈂️', '🛂', '🛃', '🛄', '🛅', '🛗', '🚹', '🚺', '🚼', '🚻', '🚮', '🎦', '📶', '🈁', '🔣', 'ℹ️', '🔤', '🔡', '🔠', '🆖', '🆗', '🆙', '🆒', '🆕', '🆓', '0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', '🔢', '#️⃣', '*️⃣', '⏏️', '▶️', '⏸️', '⏯️', '⏹️', '⏺️', '⏭️', '⏮️', '⏩', '⏪', '⏫', '⏬', '◀️', '🔼', '🔽', '➡️', '⬅️', '⬆️', '⬇️', '↗️', '↘️', '↙️', '↖️', '↕️', '↔️', '↪️', '↩️', '⤴️', '⤵️', '🔀', '🔁', '🔂', '🔄', '🔃', '🎵', '🎶', '➕', '➖', '➗', '✖️', '♾️', '💲', '💱', '™️', '©️', '®️', '〰️', '➰', '➿', '🔚', '🔙', '🔛', '🔝', '🔜', '✔️', '☑️', '🔘', '⚪', '⚫', '🔴', '🔵', '🟤', '🟣', '🟢', '🟡', '🟠', '🔺', '🔻', '🔸', '🔹', '🔶', '🔷', '🔳', '🔲', '▪️', '▫️', '◾', '◽', '◼️', '◻️', '⬛', '⬜', '🟧', '🟦', '🟥', '🟫', '🟪', '🟩', '🟨', '🔈', '🔇', '🔉', '🔊', '🔔', '🔕', '📣', '📢', '🗨️', '👁\u200d🗨', '💬', '💭', '🗯️', '♠️', '♣️', '♥️', '♦️', '🃏', '🎴', '🀄', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚', '🕛', '🕜', '🕝', '🕞', '🕟', '🕠', '🕡', '🕢', '🕣', '🕤', '🕥', '🕦', '🕧', '♀️', '♂️', '⚧', '⚕️', '🇿', '🇾', '🇽', '🇼', '🇻', '🇺', '🇹', '🇸', '🇷', '🇶', '🇵', '🇴', '🇳', '🇲', '🇱', '🇰', '🇯', '🇮', '🇭', '🇬', '🇫', '🇪', '🇩', '🇨', '🇧', '🇦', '🏳️', '🏴', '🏁', '🚩', '🏳️\u200d🌈', '🏳️\u200d⚧️', '🏴\u200d☠️', '🇦🇫', '🇦🇽', '🇦🇱', '🇩🇿', '🇦🇸', '🇦🇩', '🇦🇴', '🇦🇮', '🇦🇶', '🇦🇬', '🇦🇷', '🇦🇲', '🇦🇼', '🇦🇺', '🇦🇹', '🇦🇿', '🇧🇸', '🇧🇭', '🇧🇩', '🇧🇧', '🇧🇾', '🇧🇪', '🇧🇿', '🇧🇯', '🇧🇲', '🇧🇹', '🇧🇴', '🇧🇦', '🇧🇼', '🇧🇷', '🇮🇴', '🇻🇬', '🇧🇳', '🇧🇬', '🇧🇫', '🇧🇮', '🇰🇭', '🇨🇲', '🇨🇦', '🇮🇨', '🇨🇻', '🇧🇶', '🇰🇾', '🇨🇫', '🇹🇩', '🇨🇱', '🇨🇳', '🇨🇽', '🇨🇨', '🇨🇴', '🇰🇲', '🇨🇬', '🇨🇩', '🇨🇰', '🇨🇷', '🇨🇮', '🇭🇷', '🇨🇺', '🇨🇼', '🇨🇾', '🇨🇿', '🇩🇰', '🇩🇯', '🇩🇲', '🇩🇴', '🇪🇨', '🇪🇬', '🇸🇻', '🇬🇶', '🇪🇷', '🇪🇪', '🇪🇹', '🇪🇺', '🇫🇰', '🇫🇴', '🇫🇯', '🇫🇮', '🇫🇷', '🇬🇫', '🇵🇫', '🇹🇫', '🇬🇦', '🇬🇲', '🇬🇪', '🇩🇪', '🇬🇭', '🇬🇮', '🇬🇷', '🇬🇱', '🇬🇩', '🇬🇵', '🇬🇺', '🇬🇹', '🇬🇬', '🇬🇳', '🇬🇼', '🇬🇾', '🇭🇹', '🇭🇳', '🇭🇰', '🇭🇺', '🇮🇸', '🇮🇳', '🇮🇩', '🇮🇷', '🇮🇶', '🇮🇪', '🇮🇲', '🇮🇱', '🇮🇹', '🇯🇲', '🇯🇵', '🎌', '🇯🇪', '🇯🇴', '🇰🇿', '🇰🇪', '🇰🇮', '🇽🇰', '🇰🇼', '🇰🇬', '🇱🇦', '🇱🇻', '🇱🇧', '🇱🇸', '🇱🇷', '🇱🇾', '🇱🇮', '🇱🇹', '🇱🇺', '🇲🇴', '🇲🇰', '🇲🇬', '🇲🇼', '🇲🇾', '🇲🇻', '🇲🇱', '🇲🇹', '🇲🇭', '🇲🇶', '🇲🇷', '🇲🇺', '🇾🇹', '🇲🇽', '🇫🇲', '🇲🇩', '🇲🇨', '🇲🇳', '🇲🇪', '🇲🇸', '🇲🇦', '🇲🇿', '🇲🇲', '🇳🇦', '🇳🇷', '🇳🇵', '🇳🇱', '🇳🇨', '🇳🇿', '🇳🇮', '🇳🇪', '🇳🇬', '🇳🇺', '🇳🇫', '🇰🇵', '🇲🇵', '🇳🇴', '🇴🇲', '🇵🇰', '🇵🇼', '🇵🇸', '🇵🇦', '🇵🇬', '🇵🇾', '🇵🇪', '🇵🇭', '🇵🇳', '🇵🇱', '🇵🇹', '🇵🇷', '🇶🇦', '🇷🇪', '🇷🇴', '🇷🇺', '🇷🇼', '🇼🇸', '🇸🇲', '🇸🇹', '🇸🇦', '🇸🇳', '🇷🇸', '🇸🇨', '🇸🇱', '🇸🇬', '🇸🇽', '🇸🇰', '🇸🇮', '🇬🇸', '🇸🇧', '🇸🇴', '🇿🇦', '🇰🇷', '🇸🇸', '🇪🇸', '🇱🇰', '🇧🇱', '🇸🇭', '🇰🇳', '🇱🇨', '🇵🇲', '🇻🇨', '🇸🇩', '🇸🇷', '🇸🇿', '🇸🇪', '🇨🇭', '🇸🇾', '🇹🇼', '🇹🇯', '🇹🇿', '🇹🇭', '🇹🇱', '🇹🇬', '🇹🇰', '🇹🇴', '🇹🇹', '🇹🇳', '🇹🇷', '🇹🇲', '🇹🇨', '🇻🇮', '🇹🇻', '🇺🇬', '🇺🇦', '🇦🇪', '🇬🇧', '🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f', '🏴\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f', '🏴\U000e0067\U000e0062\U000e0077\U000e006c\U000e0073\U000e007f', '🇺🇸', '🇺🇾', '🇺🇿', '🇻🇺', '🇻🇦', '🇻🇪', '🇻🇳', '🇼🇫', '🇪🇭', '🇾🇪', '🇿🇲', '🇿🇼', '🇦🇨', '🇧🇻', '🇨🇵', '🇪🇦', '🇩🇬', '🇭🇲', '🇲🇫', '🇸🇯', '🇹🇦', '🇺🇲', '🇺🇳']
EMOJI_REGEX = re.compile("<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>|"+"|".join(re.escape(c) for c in sorted(EMOJI_LIST, key=len, reverse=True)))

NUMBER_REGEX = re.compile(r"^\(([0-9]|10|inf|infinity)-([0-9]|10|inf|infinity)\)", flags=re.IGNORECASE)
LETTER_REGEX = re.compile(r"^\(([a-z])-([a-z])\)", flags=re.IGNORECASE)


class ReactionPolls(commands.Cog):
    """
    Poll Channels w/ Auto-Reactions

    Set up poll channels in which reactions with emojis contained in messages are automatically added.
    In addition, reactions with the respective numbers and letters will be added (up to the reaction limit) when a range is input in the form of `(x-x)` at the beginning of a message.

    Range Examples:
        - `(1-10) What did you think of that event?`
        - `(A-F) What do you think your grade is?`
        - `(0-infinity) How many books have you read?`

    In that last example, the reactions for the numbers 0-10 would be added, then the infinity emoji (`inf` can also be written instead).
    Note: this currently does not support skin tones due to the Unicode mess that creates for regular expression matching.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {"toggle": True, "channels": {}}
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_message")
    async def _message_listener(self, message: discord.Message):
        if not message.guild:
            return

        settings = await self.config.guild(message.guild).all()
        ch_settings = settings["channels"].get(str(message.channel.id))

        # Ignore these messages
        if (
                await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                not settings["toggle"] or  # ReactionPolls toggled off
                message.author.bot or  # Message author is a bot
                not ch_settings or  # Message not in a ReactionPoll channel
                not settings["channels"][str(message.channel.id)]["toggle"] or  # ReactionPoll channel toggled off
                not message.channel.permissions_for(message.guild.me).add_reactions  # Cannot add reactions
        ):
            return

        m = message.content
        numbers = re.match(NUMBER_REGEX, m)
        letters = re.match(LETTER_REGEX, m)
        emojis = re.findall(EMOJI_REGEX, m)

        nothing = True
        reactions_to_add = []

        # Number range was included
        if numbers:
            nothing = False

            start = int(numbers.group(1)) if not numbers.group(1).startswith("inf") else 11
            end = int(numbers.group(2)) if not numbers.group(2).startswith("inf") else 11

            if start <= end:
                for i in range(start, end + 1, 1):
                    reactions_to_add.append(NUMBER_REACTIONS[i])
            else:
                for i in range(start, end - 1, -1):
                    reactions_to_add.append(NUMBER_REACTIONS[i])

        # Letter range was included
        if letters:
            nothing = False

            start = ord(letters.group(1))
            end = ord(letters.group(2))

            if start <= end:
                for i in range(start, end + 1, 1):
                    reactions_to_add.append(LETTER_REACTIONS[chr(i)])
            else:
                for i in range(start, end - 1, -1):
                    reactions_to_add.append(LETTER_REACTIONS[chr(i)])

        # Emojis were detected in message content
        if emojis:
            nothing = False
            
            for e in emojis:
                reactions_to_add.append(e)

        # None of the above was included, use defaults
        if nothing:
            for e in ch_settings["defaults"]:
                reactions_to_add.append(e)

        # Allow up to 20 reactions to try adding
        if len(reactions_to_add) > 20:
            reactions_to_add = reactions_to_add[:20]

        # Add reactions
        for r in reactions_to_add:
            try:
                await message.add_reaction(r)
            except discord.HTTPException:
                pass

    @commands.Cog.listener("on_message_edit")
    async def _edit_listener(self, before, after):
        await self._message_listener(after)

    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.group(name="reactionpolls", aliases=["rpolls"])
    async def _reaction_polls(self, ctx: commands.Context):
        """Settings for ReactionPolls"""

    @_reaction_polls.command(name="setchannel")
    async def _set_channel(self, ctx: commands.Context, channel: discord.TextChannel, *default_emojis: str):
        """Set a ReactionPoll channel and its default emojis (e.g. thumbs-up and down) for messages where no auto-reactions were detected."""

        for emoji in default_emojis:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                return await ctx.send(f"There was an error adding a test reaction for: {emoji}")

        async with self.config.guild(ctx.guild).channels() as settings:
            settings[str(channel.id)] = {
                "toggle": True,
                "defaults": default_emojis
            }

        return await ctx.send(f"{channel.mention} has been added as a ReactionPoll channel for this server.")

    @_reaction_polls.command(name="removechannel")
    async def _remove_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Remove a ReactionPoll channel."""

        async with self.config.guild(ctx.guild).channels() as settings:
            if str(channel.id) not in settings.keys():
                return await ctx.send(f"{channel.mention} is not a set ReactionPoll channel!")

            del settings[str(channel.id)]

        return await ctx.send(f"{channel.mention} is no longer a ReactionPoll channel for this server.")

    @_reaction_polls.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], true_or_false: bool):
        """Toggle any or all ReactionPoll channel(s)."""

        if not channel:
            await self.config.guild(ctx.guild).toggle.set(true_or_false)

        else:
            async with self.config.guild(ctx.guild).channels() as settings:
                if str(channel.id) not in settings.keys():
                    return await ctx.send(f"{channel.mention} is not a set ReactionPoll channel!")

                settings[str(channel.id)]["toggle"] = true_or_false

        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @_reaction_polls.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the current settings for ReactionPolls."""

        async with self.config.guild(ctx.guild).channels() as channels:

            embed = discord.Embed(
                title="Settings for ReactionPolls",
                description=f"**Toggle:** {await self.config.guild(ctx.guild).toggle()}\n\n",
                color=await ctx.embed_color()
            )

            for ch, ch_set in channels.items():
                if channel := ctx.guild.get_channel(int(ch)):
                    embed.description += f"{channel.mention} ({ch_set['toggle']}): {' '.join(ch_set['defaults']) if ch_set['defaults'] else None}\n"
                else:
                    del channels[ch]

        return await ctx.send(embed=embed)
