# CSNETWK_MP

### An implementation of the [Local Social Networking Protocol (LSNP)](https://docs.google.com/document/d/1DcymwZjUVcPXOps-dEgv-pvsCBtRUgKi3cOj_jULzas/edit?tab=t.0#bookmark=id.2vyk3jhpju68) for the partial fulfillment of CSNETWK Machine Project

# How to run

```
python app.py <display_name> <user_name> [avatar_source_file]
```

> [!NOTE]  
> avatar_source_file is optional

# Contributing Workflow

1. **Create a new branch** from the `dev` branch for your feature or bugfix:
   ```
   git checkout dev
   git pull
   git checkout -b feat/your-feature-name
   ```
2. **Make your changes** in your branch. Write clear, concise commit messages.
3. **Test your changes** locally to ensure nothing is broken.
4. **Push your branch** to the repository:
   ```
   git push origin feat/your-feature-name
   ```
5. **Open a Pull Request (PR)** to the `dev` branch. Describe your changes and reference any related issues.
6. **Request a review** from a maintainer or team member.
7. **Address feedback** and make any requested changes.
8. Once approved, your PR will be merged. You may then delete your branch.

**Tips:**

- Keep your branches focused on a single feature or fix.
- Pull the latest changes from `dev` before starting new work.
- Use descriptive branch names (e.g., `feat/follow-broadcast`, `fix/peer-discovery`).
- Follow code style and documentation guidelines.

## Task Distribution Table

| Task/Role                               | Esponilla | Tan      | Member 3 | Member 4 |
| --------------------------------------- | --------- | -------- | -------- | -------- |
| **Network Communication**               |           |          |          |          |
| UDP Socket Setup                        | Primary   |          |          |          |
| mDNS Discovery Integration              | Primary   |          |          |          |
| IP Address Logging                      | Primary   |          |          |          |
| **Core Feature Implementation**         |           |          |          |          |
| Core Messaging (POST, DM, LIKE, FOLLOW) |           | Primary  |          |          |
| File Transfer (Offer, Chunk, ACK)       |           |          |          |          |
| Tic Tac Toe Game (with recovery)        |           |          |          |          |
| Group Creation / Messaging              |           | Primary  |          |          |
| Induced Packet Loss (Game & File)       |           |          |          |          |
| Acknowledgement / Retry                 |           | Reviewer |          |          |
| **UI & Logging**                        |           |          |          |          |
| Verbose Mode Support                    |           | Secondary|          |          |
| Terminal Grid Display                   |           |          |          |          |
| Message Parsing & Debug Output          |           | Secondary|          |          |
| **Testing and Validation**              |           |          |          |          |
| Inter-group Testing                     |           |          |          |          |
| Correct Parsing Validation              |           |          |          |          |
| Token Expiry & IP Match                 |           | Secondary|          |          |
| **Documentation & Coordination**        |           |          |          |          |
| RFC & Project Report                    |           |          |          |          |
| Milestone Tracking & Deliverables       |           |          |          |          |
