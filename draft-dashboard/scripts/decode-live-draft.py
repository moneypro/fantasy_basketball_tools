"""Decode ESPN's versioned INIT frame without executing provider JavaScript."""
import base64
import json
import struct
import sys


def decode_init(frame):
    if not frame.startswith('INIT '):
        raise ValueError('Expected a draft INIT frame')
    data = base64.b64decode(frame.split()[1], validate=True)
    offset = 0

    def read(fmt):
        nonlocal offset
        value = struct.unpack_from('>' + fmt, data, offset)[0]
        offset += struct.calcsize('>' + fmt)
        return value

    def fields(spec):
        return {key: read(fmt) for key, fmt in (item.split(':') for item in spec.split())}

    def ints(spec):
        return fields(' '.join(key + ':i' for key in spec.split()))

    def obj(version, body):
        present = read('i')
        if present == 0:
            return None
        if present != 1 or read('i') != version:
            raise ValueError('Unsupported draft protocol version')
        return body()

    def array(body):
        count = read('i')
        if not 0 <= count <= 10000:
            raise ValueError('Invalid draft array length')
        return [body() for _ in range(count)]

    def block():
        value = ints('leagueId state')
        value['expires'] = read('q') if read('i') else None
        value.update(ints('nominationTeamIndex upForBidPlayerId highBidTeamId highBidSlotId highBidAmount'))
        return value

    def rules():
        value = ints('leagueId initialPickTime minimumPickTime nominationTime selectionTime')
        obj(1, lambda: ints('leagueId interval intervalType'))
        obj(1, lambda: ints('leagueId cutoff cutoffType'))
        ints('pauseTime nominationDelay minimumBid maximumBid')
        fields('minHigh:d maxHigh:d minCurrent:d maxCurrent:d balance:i rosterRequired:? bench:i injury:i invalid:i censor:? chat:?')

        def scoring():
            ints('leagueId scoringType')
            array(lambda: obj(3, lambda: fields('leagueId:i statId:i value:d teamStat:?')))
        obj(1, scoring)
        read('?')
        return value

    def slot():
        value = ints('leagueId slotId slotCategoryId')
        value['positions'] = array(lambda: obj(1, lambda: ints('leagueId slotCategoryId positionId')))
        return value

    def team():
        value = ints('leagueId teamId draftPosition autodraftTypeId amountLeft')
        # Consume owner records without retaining account identifiers.
        array(lambda: obj(1, lambda: fields('leagueId:i teamId:i userProfileId:i isLM:? isOnline:? isCensorEnabled:?')))
        value['rosterItems'] = array(lambda: obj(1, lambda: fields('leagueId:i teamId:i slotId:i playerId:i isKeeper:?')))
        return value

    def league():
        value = ints('leagueId draftType universeId')
        value['draftDate'] = read('q') if read('i') else None
        value['draftState'] = read('i')
        value['block'] = obj(1, block)
        obj(2, rules)
        array(lambda: obj(1, lambda: ints('leagueId positionId positionMax')))
        array(lambda: obj(1, slot))
        value['picks'] = array(lambda: obj(3, lambda: fields('leagueId:i teamId:i pickNumber:i playerId:i slotId:i bidAmount:i nominatingTeamId:i isKeeper:? autodraftTypeId:i selectorUserProfileId:i')))
        value['teams'] = array(lambda: obj(2, team))
        return value

    def draft_list():
        ints('leagueId teamId')
        read('?')
        array(lambda: obj(1, lambda: ints('leagueId teamId playerId draftValue ordinalRank')))

    def nominations():
        ints('leagueId teamId')
        array(lambda: obj(1, lambda: ints('leagueId teamId nominationId playerId initialBid')))

    def init():
        value = ints('leagueId teamId')
        value['league'] = obj(1, league)
        obj(1, draft_list)
        obj(1, nominations)
        return value

    value = obj(1, init)
    if offset != len(data) or not value or not value['league']:
        raise ValueError('Incomplete draft capture')
    return value


if __name__ == '__main__':
    value = decode_init(sys.stdin.read())
    league = value['league']
    count = len(league['teams'])
    picks = [{'overall': p['pickNumber'], 'round': (p['pickNumber'] - 1) // count + 1,
              'teamId': p['teamId'], 'playerId': p['playerId']}
             for p in league['picks'] if p and p['playerId'] > 0]
    print(json.dumps({'leagueId': value['leagueId'], 'picks': picks}))
