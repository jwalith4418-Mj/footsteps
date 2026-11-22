"""Public information rules and the role assignment disclosed to this seat."""

NOMINATION_VISIBILITY = (
    "Everyone sees who passed or who nominated whom for removal before voting. "
    "Ballots are revealed together by seat after voting closes."
)

COMMON_KNOWLEDGE = (
    "The starting team sizes and this information rule are common knowledge. Every seat knows "
    "them and knows that everyone else knows them. Blue players are told only their own "
    "alignment. Every Red player knows the complete lineup of both teams from setup. "
    f"{NOMINATION_VISIBILITY} An elimination is public. Roles are revealed publicly at game end. "
    "Discussion is public: every seat sees each remark and who said it. You and players on "
    "either team may tell the truth, lie, bluff, or stay silent. Check claims against public "
    "events and the private facts your seat is entitled to know. Speaking grants no extra "
    "way to verify a role, hand, or intention. A promised vote is not binding."
)


def role_information(snapshot):
    state, seat = snapshot["state"], snapshot["seat"]
    private = {"seat": seat, "alignment": state["role"]}
    if state["role"] == "red":
        red = {seat, *state["teammates"]}
        private["all_red_seats"] = sorted(red)
        private["all_blue_seats"] = [s for s in range(state["player_count"]) if s not in red]
    return {"common_knowledge": COMMON_KNOWLEDGE, "your_private_role_information": private}
