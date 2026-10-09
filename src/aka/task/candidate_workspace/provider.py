"""Selected workspace implementation using the original candidate mechanics."""
from aka.contracts.workspace import CandidateHandle
from .legacy import EpisodeWorktree, promote_candidate
from .snapshot import GitSnapshots


def _legacy(handle):
    return EpisodeWorktree(handle.episode, handle.base_commit, handle.branch, handle.path)


class GitCandidateWorkspace(GitSnapshots):
    def plan(self, workspace, episode, base_commit, root=None):
        handle = EpisodeWorktree.plan(workspace, episode, base_commit, root)
        return CandidateHandle(handle.episode, handle.base_commit, handle.branch, handle.path)

    def materialize(self, handle, workspace):
        _legacy(handle).materialize(workspace)

    def validate_candidate(self, handle, candidate_commit):
        return _legacy(handle).validate_candidate(candidate_commit)

    def archive(self, handle, destination, candidate_commit="HEAD"):
        return _legacy(handle).archive(destination, candidate_commit)

    def remove(self, handle, workspace):
        _legacy(handle).remove(workspace)

    def promote(self, workspace, **options):
        return promote_candidate(workspace, **options)


    def initialize_kernel(self, reference_dir, entry, arguments):
        from .initial import initialize_kernel
        return initialize_kernel(reference_dir, entry, arguments)

    def prepare_sol(self, workspace, source, **options):
        from .initial import prepare_sol
        prepare_sol(workspace, source, **options)

    def commit_sol(self, workspace):
        from .initial import commit_sol
        commit_sol(workspace)

    def install_runtime(self, workspace, atrex_bench_root=None, **options):
        from .runtime import link_runtime
        link_runtime(workspace, atrex_bench_root, **options)
