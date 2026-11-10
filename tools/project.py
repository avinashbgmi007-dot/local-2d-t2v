#!/usr/bin/env python3
"""project.py -- Project value object for the stick-figure pipeline.

Single source of truth for a project's paths and config. Replaces the scattered
`os.path.join(project, "story", ...)` recomputation across tools. Adopt
incrementally: tools may keep their own path code until migrated.

USAGE (as a library)
    from project import Project
    p = Project("projects/my_episode")
    p.shots_path          # .../story/shots.json
    p.config              # parsed config.json (cached)
    p.aspect              # "9:16"
    p.fps                 # 24

USAGE (CLI, for debugging)
    python tools/project.py projects/my_episode
"""
import json
import os
import sys


class Project:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.story = os.path.join(self.root, "story")
        self.scenes = os.path.join(self.root, "scenes")
        self.build = os.path.join(self.root, "build")
        self.out = os.path.join(self.root, "out")
        self.timeline = os.path.join(self.root, "timeline")
        self.config_path = os.path.join(self.root, "config.json")
        self.shots_path = os.path.join(self.story, "shots.json")
        self._cfg = None
        self._cfg_loaded = False

    @property
    def config(self):
        if not self._cfg_loaded:
            self._cfg_loaded = True
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    self._cfg = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                self._cfg = {}
        return self._cfg if self._cfg is not None else {}

    @property
    def aspect(self):
        return self.config.get("aspect", "9:16")

    @property
    def fps(self):
        return self.config.get("fps", 24)

    @property
    def resolution(self):
        return self.config.get("resolution", "1080p")

    @property
    def title(self):
        return self.config.get("title", "")

    def exists(self):
        return os.path.isdir(self.root) and os.path.exists(self.config_path)


def _cli():
    if len(sys.argv) < 2:
        print("usage: project.py <project_dir>", file=sys.stderr)
        return 2
    p = Project(sys.argv[1])
    print("root      :", p.root)
    print("exists    :", p.exists())
    print("aspect    :", p.aspect)
    print("fps       :", p.fps)
    print("resolution:", p.resolution)
    print("title     :", p.title)
    print("shots     :", p.shots_path, os.path.exists(p.shots_path))
    print("build     :", p.build, os.path.isdir(p.build))
    print("out       :", p.out, os.path.isdir(p.out))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
