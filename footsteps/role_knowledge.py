"""Public information rules and the role assignment disclosed to this seat."""

COMMON_KNOWLEDGE = (
    "The starting team sizes and this information rule are common knowledge. Every seat knows "
    "them and knows that everyone else knows them. Good players are told only their own "
    "alignment. Every Bad player knows the complete lineup of both teams from setup. "
    "An elimination is public. Roles are revealed publicly at game end."
)


def role_information(snapshot):
    state, seat = snapshot["state"], snapshot["seat"]
    private = {"seat": seat, "alignment": state["role"]}
    if state["role"] == "bad":
        bad = {seat, *state["teammates"]}
        private["all_bad_seats"] = sorted(bad)
        private["all_good_seats"] = [s for s in range(state["player_count"]) if s not in bad]
    return {"common_knowledge": COMMON_KNOWLEDGE, "your_private_role_information": private}
