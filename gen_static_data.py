#!/usr/bin/env python3
"""Generate rich static leaderboards.json for GetRank GitHub Pages (read-only).
All content original — no scraping from other sites.
"""
import json, os

BOARDS = [
    {"name": "Best FPS Games of 2026", "category": "Gaming",
     "description": "Community-picked top competitive shooters this year.",
     "entries": [
        ("Halo Infinite: Rebirth", "ArenaFPS_Queen", "Grounded arena combat with a fresh movement kit.", 41),
        ("Overwatch 3", "TracerFan22", "Team-based hero shooter at the top of its game.", 38),
        ("Call of Duty: Black Ops 7", "GhostRider", "Fast, punishing TTK with a great ranked ladder.", 33),
        ("Counter-Strike 2", "ClutchOrKick", "The tactical classic that never stops evolving.", 30),
        ("Valorant", "SpikeRush", "Precision utility play and crisp gunfights.", 27),
        ("Apex Legends", "JumpPadJay", "Movement shooter with the best ping system in the genre.", 22),
     ]},
    {"name": "Best Open-World Games", "category": "Gaming",
     "description": "Worlds you can lose yourself in for a hundred hours.",
     "entries": [
        ("Elden Ring", "TarnishedOne", "A sprawling, punishing masterpiece of discovery.", 45),
        ("The Witcher 3", "GeraltOfRivia", "Every side quest feels like a main quest.", 40),
        ("Red Dead Redemption 2", "ArthurMorgan", "The most alive frontier ever rendered.", 36),
        ("Breath of the Wild 2", "KorokHunter", "Verticality and physics that reward curiosity.", 31),
        ("Cyberpunk 2077: Phantom Liberty", "NightCityRider", "A city that finally feels lived-in.", 25),
     ]},
    {"name": "Best Albums of the Decade", "category": "Music",
     "description": "The records that defined the last ten years.",
     "entries": [
        ("Blonde", "VinylOnly", "Frank Ocean's quiet, devastating masterpiece.", 44),
        ("To Pimp a Butterfly", "JazzHop", "Kendrick's sprawling, ambitious opus.", 40),
        ("In Rainbows (Live)", "RadioheadFan", "A band at their most human.", 29),
        ("Sour", "PopSiren", "A debut that captured a generation's heartbreak.", 24),
        ("The Slow Rush", "SynthWave", "Tame Impala's warm, hypnotic groove.", 21),
     ]},
    {"name": "Best Live Performances", "category": "Music",
     "description": "Concerts that turned into legend.",
     "entries": [
        ("Glastonbury 2025", "FestivalHead", "Three nights, one unforgettable crowd.", 33),
        ("Coachella Main Stage", "DesertEcho", "Production so good it felt cinematic.", 28),
        ("Tiny Desk Sessions", "OfficeGig", "Intimate, stripped-back, pure talent.", 26),
        ("Madison Square Garden", "BigApple", "The arena show done right.", 22),
     ]},
    {"name": "Top Indie Game Art", "category": "Art",
     "description": "Stunning pixel & concept art from indie studios.",
     "entries": [
        ("Hollow Knight: Silksong", "BugArtist", "Hand-drawn world with breathtaking scale.", 42),
        ("Cuphead", "Inkwell", "1930s cartoon style, painstakingly animated.", 37),
        ("Ori and the Will of the Wisps", "WillOWisp", "Light-drenched painterly platforming.", 34),
        ("Dead Cells", "PixelPunk", "Atmospheric pixel art that never gets old.", 27),
        ("Celeste", "MountainClimber", "Tiny sprites, enormous heart.", 25),
     ]},
    {"name": "Best Digital Illustrations", "category": "Art",
     "description": "Concept art and digital painting that wowed the community.",
     "entries": [
        ("Neon Alley", "PixelNomad", "Cyberpunk street scene with perfect color grading.", 29),
        ("Storm Gatherer", "CloudBrush", "A fantasy landscape that feels like a window.", 26),
        ("Bioluminescent Bay", "NightGlow", "Glowing detail work that rewards zooming in.", 23),
        ("The Long Walk", "MonoLine", "Minimalist composition, maximum mood.", 19),
     ]},
    {"name": "Best Street Photography", "category": "Photography",
     "description": "Award-winning street shots from around the world.",
     "entries": [
        ("Tokyo Crossing", "ShutterBug", "A frozen moment in the world's busiest scramble.", 35),
        ("Monsoon Umbrella", "RainShot", "One frame, perfect symmetry, perfect timing.", 30),
        ("The Bicycle Courier", "RushHour", "A split-second slice of city life.", 26),
        ("Last Train Home", "NightShift", "Quiet geometry of a late platform.", 22),
     ]},
    {"name": "Best Landscape Photography", "category": "Photography",
     "description": "Golden-hour and long-exposure landscapes that inspire.",
     "entries": [
        ("Antelope Canyon", "RedRock", "Light beams through centuries of carved stone.", 31),
        ("Northern Lights Over Lofoten", "AuroraChaser", "The sky on fire above a frozen fjord.", 28),
        ("Misty Rice Terraces", "MountainFog", "Layer upon layer of morning fog.", 24),
        ("Desert Dunes at Dusk", "SandRipples", "Shadows that carve the sand into art.", 20),
     ]},
    {"name": "Best AI Developer Tools", "category": "Technology",
     "description": "Tools that genuinely make shipping software faster.",
     "entries": [
        ("Claude Code", "TerminalDev", "Agentic coding in the terminal — plans, edits, runs, tests.", 46),
        ("Cursor", "IDEPro", "An editor that predicts your next diff.", 41),
        ("Copilot Workspace", "GitHubDev", "From issue to PR with a full plan in between.", 32),
        ("Aider", "DiffDriver", "Pair-programming in your terminal with git-native edits.", 28),
        ("Continue", "LocalFirst", "Open-source assistant that runs against any model.", 25),
        ("Windsurf", "CascadeDev", "Agentic flow that reads your whole codebase.", 21),
     ]},
    {"name": "Best Productivity Apps", "category": "Technology",
     "description": "Apps that earn their place on the home screen.",
     "entries": [
        ("Notion", "WorkspaceOne", "One place for docs, wikis, and projects.", 34),
        ("Raycast", "LauncherPro", "A launcher that replaced five other apps.", 30),
        ("Obsidian", "GraphNote", "Local-first notes on a graph of your making.", 27),
        ("Linear", "IssueFlow", "Issues that feel fast because they are.", 23),
     ]},
    {"name": "Best Esports Teams", "category": "Sports",
     "description": "The orgs dominating the competitive circuit right now.",
     "entries": [
        ("T1", "MidLaneKing", "The dynasty that refuses to fade.", 33),
        ("G2 Esports", "ClutchMaster", "Europe's most explosive roster.", 28),
        ("NAVI", "AWPGod", "CS2 majors and a never-say-die attitude.", 25),
        ("Team Liquid", "DotaDynasty", "Consistent, deep runs every season.", 22),
     ]},
    {"name": "Best Cricket Players", "category": "Sports",
     "description": "The finest talents in world cricket right now.",
     "entries": [
        ("Virat Kohli", "ChaseMaster", "The run-chaser who never blinks.", 38),
        ("Jasprit Bumrah", "YorkerKing", "A death bowler who bends physics.", 35),
        ("Shubman Gill", "CoverDrive", "Silky timing, endless appetite for runs.", 29),
        ("Rohit Sharma", "Hitman", "Pull shots that clear the stadium.", 26),
        ("Mohammed Shami", "SwingBowler", "Seam bowling at its most clinical.", 22),
     ]},
]

def build():
    stats = {"leaderboards": len(BOARDS), "entries": 0, "votes": 0}
    cats = []
    boards = []
    for i, b in enumerate(BOARDS, 1):
        if b["category"] not in cats:
            cats.append(b["category"])
        entries = []
        total_votes = 0
        for title, submitter, desc, score in b["entries"]:
            entries.append({
                "id": f"{i}-{len(entries)+1}", "title": title,
                "submitter": submitter, "description": desc, "score": score,
            })
            total_votes += score
        stats["entries"] += len(entries)
        stats["votes"] += total_votes
        boards.append({
            "id": str(i), "name": b["name"], "category": b["category"],
            "description": b["description"],
            "entry_count": len(entries), "vote_count": total_votes,
            "entries": entries,
        })
    return {"leaderboards": boards, "categories": cats, "stats": stats}

def main():
    out = os.path.join(os.path.dirname(__file__), "frontend", "data", "leaderboards.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    data = build()
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {out}")
    print(f"  boards={data['stats']['leaderboards']} entries={data['stats']['entries']} votes={data['stats']['votes']} categories={data['categories']}")

if __name__ == "__main__":
    main()
